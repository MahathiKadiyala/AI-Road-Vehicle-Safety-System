"""Comprehensive unit tests for Phase 5.2: Accident-Risk Dataset Pipeline & Prediction Service.

Tests cover:
1. Dataset schema and missing-file validation.
2. Invalid target labels and out-of-bounds numeric feature detection.
3. Class imbalance warnings.
4. Train/test data leakage prevention:
   - Location-aware segment partitioning (zero segment overlap across sets).
   - Time-based holdout splitting (chronological integrity).
5. Model status diagnostic endpoint (GET /api/v1/risk/status).
6. Prediction request validation (422 Unprocessable Entity on invalid inputs).
7. Unavailable model response (HTTP 503 MODEL_UNAVAILABLE - no fake scores).
8. Distinguishing unavailable model states from genuine "Low Risk".
9. Phase 5.1 spatial hazard density integration into the risk workflow.
"""
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ml.risk.dataset_pipeline import (
    validate_dataset_schema,
    time_and_location_aware_split,
)
from app.ml.risk.predictor import risk_predictor
from app.schemas.risk import RiskPredictionRequest


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "sample_accident_records.csv"


# ==============================================================================
# 1. Dataset Ingestion & Schema Validation Tests
# ==============================================================================

def test_validate_dataset_schema_on_test_fixture():
    """Verify that sample software test fixture satisfies the schema requirements."""
    report = validate_dataset_schema(SAMPLE_CSV_PATH)
    assert report.is_valid is True
    assert report.total_records == 8
    assert report.target_column == "target_high_accident_risk"
    assert "0" in report.class_distribution
    assert "1" in report.class_distribution
    assert report.class_distribution["0"] == 5
    assert report.class_distribution["1"] == 3
    assert len(report.validation_errors) == 0


def test_validate_dataset_schema_missing_file():
    """Verify missing file handling produces a clear invalid report without crashing."""
    report = validate_dataset_schema(FIXTURES_DIR / "non_existent_file.csv")
    assert report.is_valid is False
    assert report.total_records == 0
    assert any("does not exist" in err for err in report.validation_errors)


def test_validate_dataset_schema_invalid_bounds(tmp_path):
    """Verify out-of-bounds latitude/longitude and invalid target labels are flagged."""
    bad_csv = tmp_path / "bad_records.csv"
    bad_csv.write_text(
        "segment_id,timestamp,latitude,longitude,road_classification,speed_limit_kmh,surface_condition,lighting_condition,weather_condition,pothole_count_nearby,crack_count_nearby,hazard_density_per_km,target_high_accident_risk\n"
        "SEG_BAD,2026-01-01T08:00:00Z,105.0,77.5946,urban_arterial,50.0,dry,daylight,clear,1,0,0.32,99\n",
        encoding="utf-8"
    )
    report = validate_dataset_schema(bad_csv)
    # Latitude > 90 produces a warning; target label 99 produces an error
    assert report.is_valid is False
    assert any("target label '99'" in err for err in report.validation_errors)
    assert any("out of bounds" in warn for warn in report.validation_warnings)


# ==============================================================================
# 2. Train/Test Data Leakage Prevention Tests
# ==============================================================================

def test_location_aware_holdout_prevents_segment_leakage():
    """Verify location-aware splitting ensures whole segments are kept disjoint across train and test."""
    records = [
        {"segment_id": "SEG_A", "val": 1},
        {"segment_id": "SEG_A", "val": 2},
        {"segment_id": "SEG_B", "val": 3},
        {"segment_id": "SEG_B", "val": 4},
        {"segment_id": "SEG_C", "val": 5},
        {"segment_id": "SEG_D", "val": 6},
    ]
    train, test = time_and_location_aware_split(records, holdout_fraction=0.25, split_method="location")
    train_segments = {r["segment_id"] for r in train}
    test_segments = {r["segment_id"] for r in test}

    # Strict assertion: intersection of segment IDs must be empty (ZERO leakage)
    assert len(train_segments.intersection(test_segments)) == 0
    assert len(train) > 0
    assert len(test) > 0


def test_time_aware_holdout_prevents_temporal_leakage():
    """Verify time-based splitting places chronologically latest records into the test set."""
    records = [
        {"timestamp": "2026-01-01T00:00:00Z", "id": 1},
        {"timestamp": "2026-01-03T00:00:00Z", "id": 3},
        {"timestamp": "2026-01-02T00:00:00Z", "id": 2},
        {"timestamp": "2026-01-04T00:00:00Z", "id": 4},
    ]
    train, test = time_and_location_aware_split(records, holdout_fraction=0.50, split_method="time")
    assert len(train) == 2
    assert len(test) == 2

    # Earliest in train, latest in test
    assert train[0]["timestamp"] == "2026-01-01T00:00:00Z"
    assert train[1]["timestamp"] == "2026-01-02T00:00:00Z"
    assert test[0]["timestamp"] == "2026-01-03T00:00:00Z"
    assert test[1]["timestamp"] == "2026-01-04T00:00:00Z"


# ==============================================================================
# 3. Model Diagnostic Status Endpoint Tests (GET /api/v1/risk/status)
# ==============================================================================

@pytest.mark.asyncio
async def test_risk_model_status_endpoint():
    """Verify /risk/status honestly reports model availability and data provenance."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/risk/status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["available"] is False
        assert data["status"] in ("MODEL_UNAVAILABLE", "TRAINING_DATA_UNAVAILABLE")
        assert "Awaiting verified historical road accident records" in data["dataset_provenance"]
        assert len(data["features_expected"]) > 0
        assert "speed_limit_kmh" in data["features_expected"]
        assert "hazard_density_per_km" in data["features_expected"]


# ==============================================================================
# 4. Prediction Request Validation Tests (POST /api/v1/risk/predict)
# ==============================================================================

@pytest.mark.asyncio
async def test_predict_risk_input_validation():
    """Verify request validation rejects invalid coordinates, speed limits, and unknown enums."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid latitude (> 90)
        bad_lat = {
            "latitude": 95.0,
            "longitude": 77.5946,
            "road_classification": "urban_arterial",
        }
        resp1 = await client.post("/api/v1/risk/predict", json=bad_lat)
        assert resp1.status_code == 422

        # Invalid speed limit (< 10)
        bad_speed = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "speed_limit_kmh": 5.0,
        }
        resp2 = await client.post("/api/v1/risk/predict", json=bad_speed)
        assert resp2.status_code == 422

        # Unknown road classification
        bad_road = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "road_classification": "warp_speed_hyperloop",
        }
        resp3 = await client.post("/api/v1/risk/predict", json=bad_road)
        assert resp3.status_code == 422


# ==============================================================================
# 5. Honest Unavailable Model Guard (No Synthetic / Fake Scores)
# ==============================================================================

@pytest.mark.asyncio
async def test_predict_risk_returns_503_when_model_untrained():
    """Verify that predictions are rejected with HTTP 503 instead of fabricating fake risk scores."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        valid_payload = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "road_classification": "urban_arterial",
            "speed_limit_kmh": 50.0,
            "surface_condition": "dry",
            "lighting_condition": "daylight",
            "weather_condition": "clear",
            "search_radius_meters": 1000.0,
        }
        resp = await client.post("/api/v1/risk/predict", json=valid_payload)
        assert resp.status_code == 503
        data = resp.json()

        detail = data.get("detail", {})
        assert detail.get("error") == "MODEL_UNAVAILABLE"
        assert "not trained" in detail.get("message", "").lower()

        # Crucial safeguard: verify it does NOT default to a fake "Low Risk"
        assert "risk_tier" not in detail or detail["risk_tier"] != "Low"

        # Verify spatial hazard density is returned even when model is unavailable
        assert "spatial_hazard_density" in detail
        assert "total_hazards" in detail["spatial_hazard_density"]


# ==============================================================================
# 6. Phase 7: Evaluation Metrics & Calibration Unit Tests
# ==============================================================================

def test_metrics_confusion_matrix_and_classification():
    """Verify exact calculation of confusion matrix, precision, recall, F1, and accuracy."""
    from app.ml.risk.metrics import compute_classification_metrics, compute_confusion_matrix

    y_true = [1, 1, 0, 0, 1, 0]
    y_pred = [1, 0, 0, 0, 1, 1]

    cm = compute_confusion_matrix(y_true, y_pred)
    assert cm["tp"] == 2
    assert cm["fp"] == 1
    assert cm["tn"] == 2
    assert cm["fn"] == 1

    metrics = compute_classification_metrics(y_true, y_pred)
    assert metrics["accuracy"] == round(4 / 6, 4)
    assert metrics["precision"] == round(2 / 3, 4)
    assert metrics["recall"] == round(2 / 3, 4)
    assert metrics["f1"] == round(2 / 3, 4)
    assert metrics["specificity"] == round(2 / 3, 4)


def test_metrics_roc_auc_and_pr_auc():
    """Verify ROC-AUC and PR-AUC trapezoidal integration."""
    from app.ml.risk.metrics import compute_roc_auc, compute_pr_auc

    # Perfect ranking
    y_true = [1, 1, 0, 0]
    y_prob = [0.9, 0.8, 0.2, 0.1]
    assert compute_roc_auc(y_true, y_prob) == 1.0
    assert compute_pr_auc(y_true, y_prob) == 1.0

    # Inverted ranking
    y_prob_inv = [0.1, 0.2, 0.8, 0.9]
    assert compute_roc_auc(y_true, y_prob_inv) == 0.0

    # Edge cases (all positive or all negative)
    assert compute_roc_auc([1, 1, 1], [0.9, 0.5, 0.2]) == 0.5
    assert compute_roc_auc([0, 0, 0], [0.9, 0.5, 0.2]) == 0.5


def test_metrics_brier_score_and_calibration():
    """Verify Brier calibration score and binned Expected Calibration Error (ECE)."""
    from app.ml.risk.metrics import compute_brier_score, compute_calibration_curve

    y_true = [1, 0, 1, 0]
    # Perfect probabilities
    assert compute_brier_score(y_true, [1.0, 0.0, 1.0, 0.0]) == 0.0
    # Worst probabilities
    assert compute_brier_score(y_true, [0.0, 1.0, 0.0, 1.0]) == 1.0

    calib = compute_calibration_curve(y_true, [0.9, 0.1, 0.8, 0.2], n_bins=5)
    assert "expected_calibration_error" in calib
    assert len(calib["bins"]) == 5
    assert calib["expected_calibration_error"] >= 0.0


def test_comprehensive_evaluate_risk_model():
    """Verify evaluate_risk_model outputs all required Phase 7 metrics."""
    from app.ml.risk.metrics import evaluate_risk_model

    y_true = [1, 0, 1, 1, 0, 0, 1, 0]
    y_prob = [0.85, 0.15, 0.70, 0.90, 0.25, 0.10, 0.65, 0.30]

    report = evaluate_risk_model(y_true, y_prob, threshold=0.5, n_calibration_bins=4)
    assert "roc_auc" in report
    assert "pr_auc" in report
    assert "brier_score" in report
    assert "accuracy" in report
    assert "f1" in report
    assert "confusion_matrix" in report
    assert "calibration_bins" in report
    assert report["roc_auc"] >= 0.8  # Strong ranking for this sample


# ==============================================================================
# 7. Phase 7: Training Pipeline and Predictor Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_reproducible_risk_training_pipeline_and_predictor(tmp_path):
    """Verify end-to-end training pipeline, artifact serialization, and live prediction execution."""
    from app.ml.risk.train import train_risk_model
    from app.ml.risk.predictor import AccidentRiskPredictor
    from app.schemas.risk import RiskPredictionRequest

    out_dir = tmp_path / "artifacts"

    # Train reproducible baseline model on sample CSV fixture
    results = train_risk_model(
        csv_path=SAMPLE_CSV_PATH,
        output_dir=out_dir,
        split_method="location",
        holdout_fraction=0.25,
        seed=42,
        algorithm="logistic",
    )

    assert Path(results["artifact_path"]).exists()
    assert Path(results["metadata_path"]).exists()
    assert "roc_auc" in results["metrics"]
    assert "brier_score" in results["metrics"]

    # Verify custom predictor initializes and reports MODEL_AVAILABLE
    predictor = AccidentRiskPredictor(model_artifact_path=str(results["artifact_path"]))
    status = predictor.get_status()
    assert status.available is True
    assert status.status == "MODEL_AVAILABLE"
    assert status.evaluation_metrics is not None

    # Test prediction execution
    req = RiskPredictionRequest(
        latitude=12.9716,
        longitude=77.5946,
        road_classification="urban_arterial",
        speed_limit_kmh=50.0,
        surface_condition="dry",
        lighting_condition="daylight",
        weather_condition="clear",
        vehicle_safety_score=85.0,
    )
    spatial_density = {
        "pothole_count": 2,
        "crack_count": 5,
        "density_per_sqkm": 3.5,
    }

    pred_resp = await predictor.predict_async(req, spatial_density)
    assert 0.0 <= pred_resp.risk_score <= 100.0
    assert pred_resp.risk_tier in ("Low", "Medium", "High", "Critical")
    assert len(pred_resp.feature_contributions) > 0
    assert any(f.feature_name == "vehicle_safety_score" for f in pred_resp.feature_contributions)
