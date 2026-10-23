"""Pydantic schemas for Vehicle Safety Assessment."""
from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class VehicleAssessmentCreate(BaseModel):
    """Input payload for preliminary vehicle evaluation."""
    make: str = Field(..., max_length=80, json_schema_extra={"example": "Maruti Suzuki"})
    model: str = Field(..., max_length=80, json_schema_extra={"example": "Swift"})
    year: int = Field(..., ge=1970, le=2030, json_schema_extra={"example": 2018})
    odometer_km: float = Field(..., ge=0, json_schema_extra={"example": 52000.0})
    brake_pad_thickness_mm: float = Field(..., ge=0.0, le=25.0, description="Measured brake pad thickness in mm", json_schema_extra={"example": 4.5})
    tyre_tread_depth_mm: float = Field(..., ge=0.0, le=20.0, description="Measured tyre tread depth in mm", json_schema_extra={"example": 3.2})
    service_records_count: int = Field(default=0, ge=0)
    past_accidents_count: int = Field(default=0, ge=0)
    disclaimer_acknowledged: bool = Field(
        ...,
        description="User must acknowledge this is a preliminary estimate, not a certified physical inspection."
    )


class VehicleAssessmentRead(VehicleAssessmentCreate):
    """Output schema for preliminary vehicle evaluation results."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preliminary_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: str
    critical_warnings: List[str]
    legal_disclaimer_version: str
    created_at: datetime
