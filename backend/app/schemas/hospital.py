"""Pydantic schemas for Hospital and Trauma Center reference data."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class HospitalBase(BaseModel):
    """Core hospital attributes."""
    name: str = Field(..., max_length=180)
    facility_type: str = Field(default="General Hospital")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    has_emergency_service: bool = True
    total_beds_reference: Optional[int] = Field(
        None,
        description="Static reference capacity; not live telemetry in MVP."
    )
    is_verified_facility: bool = True


class HospitalRead(HospitalBase):
    """Output schema for hospital locations."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
