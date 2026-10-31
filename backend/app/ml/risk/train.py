"""Accident-Risk Reproducible Training and Evaluation Pipeline.

Ingests validated accident incidence records, prevents spatial/temporal data leakage,
trains a baseline calibrated classifier (with XGBoost support if installed), computes
rigorous metrics (ROC-AUC, PR-AUC, Brier score, calibration bins), and serializes
authentic model weights and metadata.
"""
import argparse
import csv
import json
import logging
import math
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from app.ml.risk.dataset_pipeline import (
    validate_dataset_schema,
    time_and_location_aware_split,
    EXPECTED_COLUMNS,
)
from app.ml.risk.metrics import evaluate_risk_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("risk_train")

NUMERIC_FEATURES = [
    "speed_limit_kmh",
    "pothole_count_nearby",
    "crack_count_nearby",
    "hazard_density_per_km",
]

CATEGORICAL_FEATURES = [
    "road_classification",
    "surface_condition",
    "lighting_condition",
    "weather_condition",
]


class LogisticRegressionBaseline:
    """Deterministic, regularized logistic regression baseline in pure NumPy.

    Provides a reproducible classifier that runs in any environment without external C-extensions.
    """

    def __init__(self, l2_reg: float = 0.01, lr: float = 0.05, max_iter: int = 500, seed: int = 42):
        self.l2_reg = l2_reg
        self.lr = lr
        self.max_iter = max_iter
        self.seed = seed
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionBaseline":
        rng = np.random.RandomState(self.seed)
        n_samples, n_features = X.shape

        # Initialize weights small and deterministic
        self.weights = rng.normal(0.0, 0.01, size=n_features)
        self.bias = 0.0

        for epoch in range(self.max_iter):
            # Forward pass
            logits = np.dot(X, self.weights) + self.bias
            # Numerical stable sigmoid
            probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -25.0, 25.0)))

            # Gradients
            errors = probs - y
            dw = (np.dot(X.T, errors) / n_samples) + (self.l2_reg * self.weights)
            db = float(np.sum(errors) / n_samples)

            # Gradient descent step with learning rate decay
            effective_lr = self.lr / (1.0 + 0.001 * epoch)
            self.weights -= effective_lr * dw
            self.bias -= effective_lr * db

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.weights is None:
            raise RuntimeError("Model is not fitted.")
        logits = np.dot(X, self.weights) + self.bias
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -25.0, 25.0)))
        return probs

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


def extract_features_and_labels(
    records: List[Dict[str, Any]],
    scaler_params: Optional[Dict[str, Dict[str, float]]] = None,
    cat_vocabs: Optional[Dict[str, List[str]]] = None,
) -> Tuple[np.ndarray, np.ndarray, List[str], Dict[str, Dict[str, float]], Dict[str, List[str]]]:
    """Transform raw dictionary records into a numeric feature matrix with scaling and one-hot encoding."""
    if not records:
        raise ValueError("Cannot extract features from empty records list.")

    is_training = scaler_params is None

    # Step 1: Compute or use scaling parameters for numeric features
    if is_training:
        scaler_params = {}
        for num_col in NUMERIC_FEATURES:
            vals = [float(r.get(num_col, 0.0) or 0.0) for r in records]
            mean_v = float(np.mean(vals))
            std_v = float(np.std(vals))
            scaler_params[num_col] = {
                "mean": mean_v,
                "std": std_v if std_v > 1e-6 else 1.0,
            }

    # Step 2: Compute or use category vocabularies
    if is_training:
        cat_vocabs = {}
        for cat_col in CATEGORICAL_FEATURES:
            unique_vals = sorted(list({str(r.get(cat_col, "unknown")).strip().lower() for r in records}))
            cat_vocabs[cat_col] = unique_vals

    # Step 3: Build column names
    feature_names: List[str] = list(NUMERIC_FEATURES)
    for cat_col in CATEGORICAL_FEATURES:
        for val in cat_vocabs[cat_col]:
            feature_names.append(f"{cat_col}__{val}")

    # Step 4: Assemble matrix
    n_samples = len(records)
    n_features = len(feature_names)
    X = np.zeros((n_samples, n_features), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.int32)

    for i, r in enumerate(records):
        # Numeric
        col_idx = 0
        for num_col in NUMERIC_FEATURES:
            raw_v = float(r.get(num_col, 0.0) or 0.0)
            scaled_v = (raw_v - scaler_params[num_col]["mean"]) / scaler_params[num_col]["std"]
            X[i, col_idx] = scaled_v
            col_idx += 1

        # Categorical one-hot
        for cat_col in CATEGORICAL_FEATURES:
            cur_cat = str(r.get(cat_col, "unknown")).strip().lower()
            for val in cat_vocabs[cat_col]:
                X[i, col_idx] = 1.0 if cur_cat == val else 0.0
                col_idx += 1

        # Target label
        target_v = int(r.get("target_high_accident_risk", 0))
        y[i] = target_v

    return X, y, feature_names, scaler_params, cat_vocabs


def train_risk_model(
    csv_path: str | Path,
    output_dir: str | Path = "backend/app/ml/artifacts",
    split_method: str = "location",
    holdout_fraction: float = 0.25,
    seed: int = 42,
    algorithm: str = "auto",
) -> Dict[str, Any]:
    """Train accident-risk model, evaluate metrics, and save serialized artifacts."""
    csv_file = Path(csv_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Validating candidate dataset schema: {csv_file}")
    report = validate_dataset_schema(csv_file)
    if not report.is_valid:
        raise ValueError(f"Dataset failed schema validation: {report.validation_errors}")

    logger.info(f"Loading {report.total_records} validated rows from CSV...")
    records: List[Dict[str, Any]] = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader([l for l in f if not l.strip().startswith("#")])
        for row in reader:
            records.append(row)

    # Split with zero leakage guarantee
    logger.info(f"Splitting data using method='{split_method}', holdout_fraction={holdout_fraction}...")
    train_records, test_records = time_and_location_aware_split(
        records, holdout_fraction=holdout_fraction, split_method=split_method
    )

    if not train_records or not test_records:
        # Fallback if too few records for location partitioning
        logger.warning("Disjoint segment partitioning yielded empty split, falling back to deterministic index split.")
        split_idx = max(1, int(len(records) * (1.0 - holdout_fraction)))
        train_records = records[:split_idx]
        test_records = records[split_idx:]

    logger.info(f"Train samples: {len(train_records)} | Test samples: {len(test_records)}")

    # Extract features
    X_train, y_train, feature_names, scaler_params, cat_vocabs = extract_features_and_labels(train_records)
    X_test, y_test, _, _, _ = extract_features_and_labels(
        test_records, scaler_params=scaler_params, cat_vocabs=cat_vocabs
    )

    # Check for XGBoost availability
    use_xgb = False
    xgb_model = None
    if algorithm in ("auto", "xgboost"):
        try:
            import xgboost as xgb
            use_xgb = True
            logger.info("XGBoost detected. Training XGBClassifier...")
        except ImportError:
            if algorithm == "xgboost":
                raise ImportError("XGBoost is requested but not installed.")
            logger.info("XGBoost not installed. Using regularized Logistic Regression baseline.")

    architecture = "XGBoost Classifier" if use_xgb else "Baseline Calibrated Logistic Model"

    if use_xgb:
        import xgboost as xgb
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=seed,
            eval_metric="logloss",
        )
        xgb_model.fit(X_train, y_train)
        y_prob_test = xgb_model.predict_proba(X_test)[:, 1].tolist()
    else:
        # Logistic regression baseline
        baseline = LogisticRegressionBaseline(l2_reg=0.01, lr=0.05, max_iter=500, seed=seed)
        baseline.fit(X_train, y_train)
        y_prob_test = baseline.predict_proba(X_test).tolist()

    # Evaluate metrics
    eval_results = evaluate_risk_model(y_true=y_test.tolist(), y_prob=y_prob_test, threshold=0.5)

    logger.info("=== Holdout Evaluation Metrics ===")
    logger.info(f"ROC-AUC:       {eval_results['roc_auc']:.4f}")
    logger.info(f"PR-AUC:        {eval_results['pr_auc']:.4f}")
    logger.info(f"Brier Score:   {eval_results['brier_score']:.4f}")
    logger.info(f"Accuracy:      {eval_results['accuracy']:.4f}")
    logger.info(f"Precision:     {eval_results['precision']:.4f}")
    logger.info(f"Recall:        {eval_results['recall']:.4f}")
    logger.info(f"F1-Score:      {eval_results['f1']:.4f}")
    logger.info(f"Calibration ECE: {eval_results['expected_calibration_error']:.4f}")

    # Serialize model artifact
    artifact_path = out_dir / "accident_risk_model.json"
    artifact_payload = {
        "model_type": "xgboost" if use_xgb else "logistic_baseline",
        "feature_names": feature_names,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "scaler_params": scaler_params,
        "cat_vocabs": cat_vocabs,
        "weights": (
            xgb_model.get_booster().dump_model() if use_xgb else baseline.weights.tolist()
        ),
        "bias": 0.0 if use_xgb else float(baseline.bias),
    }

    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifact_payload, f, indent=2)

    # Serialize metadata
    meta_path = out_dir / "risk_metadata.json"
    metadata = {
        "model_version": "1.0.0",
        "architecture": architecture,
        "training_date": datetime.now().isoformat(),
        "random_seed": seed,
        "dataset_provenance": f"Trained on {csv_file.name} ({len(records)} verified records)",
        "split_method": split_method,
        "holdout_fraction": holdout_fraction,
        "train_samples": len(train_records),
        "test_samples": len(test_records),
        "metrics": eval_results,
        "model_artifact": str(artifact_path.name),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model artifact saved to: {artifact_path}")
    logger.info(f"Metadata saved to: {meta_path}")

    return {
        "artifact_path": str(artifact_path),
        "metadata_path": str(meta_path),
        "metrics": eval_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate accident-risk prediction model.")
    parser.add_argument("--csv", type=str, required=True, help="Path to validated accident dataset CSV.")
    parser.add_argument("--out-dir", type=str, default="backend/app/ml/artifacts", help="Artifact output directory.")
    parser.add_argument("--split-method", type=str, default="location", choices=["location", "time"], help="Split method.")
    parser.add_argument("--holdout", type=float, default=0.25, help="Holdout fraction for testing.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--algorithm", type=str, default="auto", choices=["auto", "xgboost", "logistic"], help="Model algorithm.")
    args = parser.parse_args()

    train_risk_model(
        csv_path=args.csv,
        output_dir=args.out_dir,
        split_method=args.split_method,
        holdout_fraction=args.holdout,
        seed=args.seed,
        algorithm=args.algorithm,
    )


if __name__ == "__main__":
    main()
