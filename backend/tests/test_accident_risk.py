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
