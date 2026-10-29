"""Pydantic schemas for Road Hazard data transfer."""
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


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

    @computed_field
    @property
    def image_url(self) -> Optional[str]:
        """Generate the static file URL for the uploaded image."""
        if not self.image_path:
            return None
        return f"/static/{self.image_path}"


class NearbyHazardSummary(BaseModel):
    """Brief summary of a hazard within proximity."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    hazard_type: str
    severity: str
    latitude: float
    longitude: float
    distance_meters: float = Field(..., ge=0.0, description="Straight-line distance from query center in meters")
    created_at: datetime


class HazardDensityResponse(BaseModel):
    """Aggregated nearby-hazard density metrics for a query coordinate and radius."""
    center_latitude: float = Field(..., ge=-90.0, le=90.0)
    center_longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(..., ge=10.0, le=50000.0)
    area_sqkm: float = Field(..., ge=0.0)
    total_hazards: int = Field(..., ge=0)
    density_per_sqkm: float = Field(..., ge=0.0)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
    critical_and_high_count: int = Field(default=0, ge=0)
    spatial_engine: str = Field(..., description="'postgis' or 'haversine_fallback'")
    hazards_with_missing_geometry_count: int = Field(default=0, ge=0)
    advisory_notes: List[str] = Field(default_factory=list)
    nearby_hazards: List[NearbyHazardSummary] = Field(default_factory=list)
