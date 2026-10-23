"""Pydantic data validation schemas."""
from app.schemas.health import HealthResponse, DatabaseHealth
from app.schemas.hazard import HazardBase, HazardCreate, HazardRead
from app.schemas.vehicle import VehicleAssessmentCreate, VehicleAssessmentRead
from app.schemas.hospital import HospitalBase, HospitalRead

__all__ = [
    "HealthResponse",
    "DatabaseHealth",
    "HazardBase",
    "HazardCreate",
    "HazardRead",
    "VehicleAssessmentCreate",
    "VehicleAssessmentRead",
    "HospitalBase",
    "HospitalRead",
]
