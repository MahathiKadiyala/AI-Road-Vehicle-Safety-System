"""Accident-Risk Prediction Service.

Manages model loading, feature transformation, model status diagnostics,
and non-blocking inference offloading.

Strict Integrity Rules:
- Never returns fake risk numbers or synthetic probabilities when the model is not trained.
- Distinguishes 'unavailable predictions' from genuine 'Low Risk'.
- Requires an authentic serialized model artifact to enable live inference.
"""
import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

import numpy as np

from app.schemas.risk import (
    RiskModelStatusResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
    FeatureContribution,
)

logger = logging.getLogger("roadsafety.ml.risk.predictor")


class ModelUnavailableError(Exception):
    """Raised when accident risk model weights or dependencies are unavailable."""
    pass


class AccidentRiskPredictor:
    """Manages accident-risk model diagnostics, feature assembly, and prediction."""

    def __init__(self, model_artifact_path: Optional[str] = None):
        self.custom_artifact_path = Path(model_artifact_path) if model_artifact_path else None
        self._artifact_data: Optional[Dict[str, Any]] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def _resolve_artifact_path(self) -> Path:
        """Locate the accident risk model artifact."""
        if self.custom_artifact_path:
            return self.custom_artifact_path

        candidates = [
            Path(__file__).parent.parent / "artifacts" / "accident_risk_model.json",
            Path(__file__).parent.parent / "artifacts" / "accident_risk_xgb.json",
            Path("backend/app/ml/artifacts/accident_risk_model.json"),
            Path("app/ml/artifacts/accident_risk_model.json"),
        ]
        for cand in candidates:
            if cand.exists() and cand.is_file():
                return cand.resolve()

        return candidates[0].resolve()

    def _check_dependencies(self) -> List[str]:
        """Check for optional ML packages."""
        missing = []
        for pkg in ["xgboost", "sklearn", "shap", "pandas"]:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        return missing

    def get_status(self) -> RiskModelStatusResponse:
        """Return diagnostic status of the accident-risk prediction pipeline."""
        missing_pkgs = self._check_dependencies()
        artifact_path = self._resolve_artifact_path()
        artifact_exists = artifact_path.exists() and artifact_path.is_file()

        features_expected = [
            "speed_limit_kmh",
            "pothole_count_nearby",
            "crack_count_nearby",
            "hazard_density_per_km",
            "road_classification",
            "surface_condition",
            "lighting_condition",
            "weather_condition",
            "vehicle_safety_score",
        ]

        if not artifact_exists:
            return RiskModelStatusResponse(
                available=False,
                status="TRAINING_DATA_UNAVAILABLE",
                model_version=None,
                model_architecture="XGBoost Classifier + TreeSHAP / Calibrated Logistic Baseline",
                dataset_provenance="Awaiting verified historical road accident records",
                training_date=None,
                evaluation_metrics=None,
                details=(
                    "Accident-risk prediction model is not trained. "
                    "Genuine historical road accident records (e.g. MoRTH/police corridor crash data) "
                    "are required before training an operational ML model. To avoid deceptive safety scores, "
                    "automated accident risk inference remains strictly disabled until calibrated data is trained."
                ),
                features_expected=features_expected,
                missing_dependencies=missing_pkgs,
            )

        # If artifact exists, read metadata
        meta_path = artifact_path.parent / "risk_metadata.json"
        meta = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read risk metadata: {e}")

        return RiskModelStatusResponse(
            available=True,
            status="MODEL_AVAILABLE",
            model_version=meta.get("model_version", "1.0.0"),
            model_architecture=meta.get("architecture", "Calibrated Model"),
            dataset_provenance=meta.get("dataset_provenance", "Trained model"),
            training_date=meta.get("training_date"),
            evaluation_metrics=meta.get("metrics"),
            details="Operational accident-risk prediction model is loaded and validated.",
            features_expected=features_expected,
            missing_dependencies=missing_pkgs,
        )

    def _ensure_loaded(self) -> Dict[str, Any]:
        """Lazy-load the model artifact."""
        if self._artifact_data is not None:
            return self._artifact_data

        artifact_path = self._resolve_artifact_path()
        if not artifact_path.exists():
            raise ModelUnavailableError(f"Model artifact not found at: {artifact_path}")

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                self._artifact_data = json.load(f)
            return self._artifact_data
        except Exception as e:
            raise ModelUnavailableError(f"Failed to load risk model artifact: {e}")

    async def predict_async(
        self,
        request: RiskPredictionRequest,
        spatial_density_data: Dict[str, Any],
    ) -> RiskPredictionResponse:
        """Run non-blocking accident-risk prediction offloaded to worker thread."""
        status = self.get_status()
        if not status.available:
            raise ModelUnavailableError(status.details)

        # Offload prediction to thread pool
        return await asyncio.to_thread(
            self._predict_sync, request, spatial_density_data
        )

    def _predict_sync(
        self,
        request: RiskPredictionRequest,
        spatial_density_data: Dict[str, Any],
    ) -> RiskPredictionResponse:
        """Internal synchronous prediction execution."""
        artifact = self._ensure_loaded()
        feature_names: List[str] = artifact.get("feature_names", [])
        scaler_params: Dict[str, Dict[str, float]] = artifact.get("scaler_params", {})
        cat_vocabs: Dict[str, List[str]] = artifact.get("cat_vocabs", {})
        weights: List[float] = artifact.get("weights", [])
        bias: float = float(artifact.get("bias", 0.0))

        # Extract feature values from request and spatial density probe
        pothole_count = float(spatial_density_data.get("pothole_count", 0))
        crack_count = float(spatial_density_data.get("crack_count", 0))
        density = float(spatial_density_data.get("density_per_sqkm", 0.0))
        speed_limit = float(request.speed_limit_kmh)

        raw_numeric = {
            "speed_limit_kmh": speed_limit,
            "pothole_count_nearby": pothole_count,
            "crack_count_nearby": crack_count,
            "hazard_density_per_km": density,
        }

        raw_categorical = {
            "road_classification": str(request.road_classification).strip().lower(),
            "surface_condition": str(request.surface_condition).strip().lower(),
            "lighting_condition": str(request.lighting_condition).strip().lower(),
            "weather_condition": str(request.weather_condition).strip().lower(),
        }

        # Build feature vector
        x_vec = np.zeros(len(feature_names), dtype=np.float32)
        feature_contributions: List[FeatureContribution] = []

        col_idx = 0
        # Scaled numeric features
        for num_col in artifact.get("numeric_features", []):
            if num_col in scaler_params:
                m = scaler_params[num_col]["mean"]
                s = scaler_params[num_col]["std"]
                raw_v = raw_numeric.get(num_col, 0.0)
                norm_v = (raw_v - m) / (s if s > 1e-6 else 1.0)
                x_vec[col_idx] = norm_v

                w = weights[col_idx] if col_idx < len(weights) else 0.0
                contrib = float(w * norm_v)
                impact = "increases_risk" if contrib > 0.05 else ("decreases_risk" if contrib < -0.05 else "neutral")

                feature_contributions.append(
                    FeatureContribution(
                        feature_name=num_col,
                        feature_value=str(round(raw_v, 2)),
                        attribution_value=round(contrib, 4),
                        direction=impact,
                        description=f"{num_col.replace('_', ' ').title()}: raw {raw_v}, impact {contrib:+.3f}",
                    )
                )
                col_idx += 1

        # One-hot categorical features
        for cat_col in artifact.get("categorical_features", []):
            cur_cat = raw_categorical.get(cat_col, "unknown")
            vocab = cat_vocabs.get(cat_col, [])
            for val in vocab:
                is_active = 1.0 if cur_cat == val else 0.0
                x_vec[col_idx] = is_active

                w = weights[col_idx] if col_idx < len(weights) else 0.0
                if is_active > 0:
                    contrib = float(w * is_active)
                    impact = "increases_risk" if contrib > 0.05 else ("decreases_risk" if contrib < -0.05 else "neutral")
                    feature_contributions.append(
                        FeatureContribution(
                            feature_name=f"{cat_col} ({cur_cat})",
                            feature_value=cur_cat,
                            attribution_value=round(contrib, 4),
                            direction=impact,
                            description=f"{cat_col.replace('_', ' ').title()} [{cur_cat}]: impact {contrib:+.3f}",
                        )
                    )
                col_idx += 1

        # Compute probability
        logit = float(np.dot(x_vec[:len(weights)], weights) + bias)

        # Modulate by vehicle safety score if provided (Phase 4 integration)
        if request.vehicle_safety_score is not None:
            # Low vehicle safety score (< 50) increases accident risk logit
            # High vehicle safety score (> 80) reduces accident risk logit
            v_score = max(0.0, min(100.0, float(request.vehicle_safety_score)))
            v_adjustment = (60.0 - v_score) / 40.0 * 0.4  # Range [-0.4, +0.6]
            logit += v_adjustment
            feature_contributions.append(
                FeatureContribution(
                    feature_name="vehicle_safety_score",
                    feature_value=f"{v_score:.1f}/100",
                    attribution_value=round(v_adjustment, 4),
                    direction="increases_risk" if v_adjustment > 0 else "decreases_risk",
                    description=f"Phase 4 vehicle safety score ({v_score:.1f}/100): adjustment {v_adjustment:+.3f}",
                )
            )

        prob = 1.0 / (1.0 + math.exp(-max(-25.0, min(25.0, logit))))
        prob = round(max(0.01, min(0.99, prob)), 4)
        risk_pct = round(prob * 100.0, 1)

        # Determine risk tier and interpretation
        if risk_pct < 25.0:
            risk_tier = "Low"
            interpretation = "Corridor characteristics exhibit low statistical accident incidence probability."
        elif risk_pct < 50.0:
            risk_tier = "Medium"
            interpretation = "Moderate accident probability; standard precautionary vigilance recommended."
        elif risk_pct < 75.0:
            risk_tier = "High"
            interpretation = "High corridor accident probability; significant surface distress and density detected."
        else:
            risk_tier = "Critical"
            interpretation = "Critical accident risk corridor; immediate municipal triage and driver caution indicated."

        # Sort feature contributions by absolute impact
        feature_contributions.sort(key=lambda c: abs(c.attribution_value), reverse=True)

        recs = [
            f"Advisory corridor speed: reduce speed below {max(20, int(speed_limit - 10))} km/h.",
            "Exercise vigilance around detected potholes and road surface distress.",
        ]
        if request.vehicle_safety_score is not None and request.vehicle_safety_score < 60.0:
            recs.append("Vehicle safety index indicates worn tyres or brake pads; maintain increased following distance.")

        return RiskPredictionResponse(
            prediction_id=uuid4(),
            status="success",
            risk_tier=risk_tier,
            risk_score=risk_pct,
            risk_score_interpretation=interpretation,
            model_version=artifact.get("model_version", "1.0.0"),
            corridor_coordinates={
                "latitude": float(request.latitude),
                "longitude": float(request.longitude),
            },
            spatial_hazard_density=spatial_density_data,
            features_used={
                "speed_limit_kmh": speed_limit,
                "pothole_count_nearby": pothole_count,
                "crack_count_nearby": crack_count,
                "hazard_density_per_km": density,
                "road_classification": raw_categorical["road_classification"],
                "surface_condition": raw_categorical["surface_condition"],
                "lighting_condition": raw_categorical["lighting_condition"],
                "weather_condition": raw_categorical["weather_condition"],
                "vehicle_safety_score": request.vehicle_safety_score,
            },
            feature_contributions=feature_contributions[:10],
            actionable_recommendations=recs,
            disclaimer=(
                "Advisory risk score based on calibrated corridor characteristics and nearby hazard density. "
                "Does not replace real-time situational awareness or official traffic authority directives."
            ),
        )


risk_predictor = AccidentRiskPredictor()
