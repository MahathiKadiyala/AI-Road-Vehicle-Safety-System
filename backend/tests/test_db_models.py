"""Test suite for database models and Pydantic validation schemas."""
import pytest
from uuid import uuid4
from pydantic import ValidationError
from app.models.hazard import Hazard
from app.models.vehicle import VehicleAssessment
from app.models.hospital import Hospital
from app.schemas.hazard import HazardCreate
from app.schemas.vehicle import VehicleAssessmentCreate


def test_hazard_model_instantiation():
    """Verify Hazard model accepts required fields."""
    h = Hazard(
        id=uuid4(),
        title="Deep Pothole on Main St",
        hazard_type="pothole",
        severity="high",
        latitude=12.9716,
        longitude=77.5946,
        source="citizen_report"
    )
    assert h.hazard_type == "pothole"
    assert h.severity == "high"
    assert h.latitude == 12.9716
    assert h.longitude == 77.5946


def test_vehicle_assessment_model_instantiation():
    """Verify VehicleAssessment model accepts required mechanical inputs."""
    v = VehicleAssessment(
        id=uuid4(),
        make="Hyundai",
        model="i20",
        year=2020,
        odometer_km=42000.0,
        brake_pad_thickness_mm=4.0,
        tyre_tread_depth_mm=3.5,
        service_records_count=4,
        past_accidents_count=0,
        preliminary_score=85.0,
        risk_tier="Low",
        critical_warnings=[],
        disclaimer_acknowledged=True
    )
    assert v.make == "Hyundai"
    assert v.preliminary_score == 85.0
    assert v.risk_tier == "Low"


def test_hospital_model_instantiation():
    """Verify Hospital model structure."""
    hosp = Hospital(
        id=uuid4(),
        name="Victoria Hospital Trauma Center",
        facility_type="Trauma Center",
        latitude=12.9634,
        longitude=77.5756,
        address="Fort Road, Bengaluru",
        contact_phone="+91-80-26701150",
        has_emergency_service=True,
        total_beds_reference=350,
        is_verified_facility=True
    )
    assert hosp.name == "Victoria Hospital Trauma Center"
    assert hosp.has_emergency_service is True


def test_hazard_schema_validation():
    """Test Pydantic validation for hazard creation."""
    # Valid payload
    payload = {
        "title": "Severe road crack",
        "description": "Transverse crack across entire lane",
        "hazard_type": "crack",
        "severity": "critical",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "source": "citizen_report"
    }
    hazard_obj = HazardCreate(**payload)
    assert hazard_obj.severity == "critical"

    # Invalid latitude
    with pytest.raises(ValidationError):
        HazardCreate(**{**payload, "latitude": 195.0})

    # Invalid hazard type
    with pytest.raises(ValidationError):
        HazardCreate(**{**payload, "hazard_type": "alien_spaceship"})
