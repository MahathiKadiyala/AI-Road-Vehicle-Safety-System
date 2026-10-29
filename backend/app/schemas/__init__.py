"""Pydantic data validation schemas."""
from app.schemas.health import HealthResponse, DatabaseHealth
from app.schemas.hazard import HazardBase, HazardCreate, HazardRead
from app.schemas.vehicle import (
    VehicleAssessmentCreate,
    VehicleAssessmentRead,
    ParameterAuditItem,
    VehicleStandardsResponse,
)
from app.schemas.hospital import HospitalBase, HospitalRead
from app.schemas.damage_detection import (
    BoundingBox,
    DamageDetectionItem,
    DamageDetectionResponse,
    DamageModelStatusResponse,
)

__all__ = [
    "HealthResponse",
    "DatabaseHealth",
    "HazardBase",
    "HazardCreate",
    "HazardRead",
    "VehicleAssessmentCreate",
    "VehicleAssessmentRead",
    "ParameterAuditItem",
    "VehicleStandardsResponse",
    "HospitalBase",
    "HospitalRead",
    "BoundingBox",
    "DamageDetectionItem",
    "DamageDetectionResponse",
    "DamageModelStatusResponse",
]
