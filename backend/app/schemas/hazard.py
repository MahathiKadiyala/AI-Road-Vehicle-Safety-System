"""Pydantic schemas for Road Hazard data transfer."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class HazardBase(BaseModel):
    """Common hazard attributes."""
    title: str = Field(..., max_length=150, description="Short title of the hazard")
    description: Optional[str] = Field(None, description="Detailed hazard context")
    hazard_type: str = Field(default="pothole", description="pothole, crack, debris, waterlogging, obstacle")
    severity: str = Field(default="medium", description="low, medium, high, critical")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")

    @field_validator("hazard_type")
    @classmethod
    def validate_hazard_type(cls, v: str) -> str:
        allowed = {"pothole", "crack", "debris", "waterlogging", "obstacle", "other"}
        if v.lower() not in allowed:
            raise ValueError(f"Hazard type must be one of {allowed}")
        return v.lower()

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"Severity must be one of {allowed}")
        return v.lower()


class HazardCreate(HazardBase):
    """Schema for hazard report submission."""
    source: str = Field(default="citizen_report")


class HazardRead(HazardBase):
    """Schema for returning hazard records."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_path: Optional[str] = None
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
