"""Pydantic schemas for Hospital and Trauma Center reference data.

Includes input schemas, spatial distance output schemas, and transparent
emergency advisory disclosures.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class HospitalBase(BaseModel):
    """Core hospital attributes."""
    name: str = Field(..., max_length=180, description="Full registered name of the facility")
    facility_type: str = Field(
        default="General Hospital",
        description="e.g. Trauma Center, Super Specialty, Multi Specialty, General Hospital"
    )
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    address: Optional[str] = Field(None, max_length=255, description="Physical street address")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Emergency reception phone number")
    has_emergency_service: bool = Field(default=True, description="Whether facility operates 24/7 emergency casualty triage")
    total_beds_reference: Optional[int] = Field(
        None,
        ge=0,
        description="Static reference capacity; not live telemetry in MVP."
    )
    is_verified_facility: bool = Field(default=True, description="Whether entry was verified against public health registry")


class HospitalCreate(HospitalBase):
    """Schema for adding a verified hospital record."""
    pass


class HospitalRead(HospitalBase):
    """Output schema for hospital locations."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class NearbyHospitalItem(BaseModel):
    """Hospital proximity record with computed straight-line distance."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    facility_type: str
    latitude: float
    longitude: float
    straight_line_distance_meters: float = Field(..., ge=0.0, description="Straight-line distance in meters")
    straight_line_distance_km: float = Field(..., ge=0.0, description="Straight-line distance in kilometers")
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    has_emergency_service: bool
    total_beds_reference: Optional[int] = None
    is_verified_facility: bool
    data_source: str = "Verified Public Health Registry Reference"


class NearbyHospitalsResponse(BaseModel):
    """Aggregated response for hospital proximity queries."""
    center_latitude: float = Field(..., ge=-90.0, le=90.0)
    center_longitude: float = Field(..., ge=-180.0, le=180.0)
    search_radius_meters: float = Field(..., ge=100.0, le=100000.0)
    total_found: int = Field(..., ge=0)
    spatial_engine: str = Field(..., description="'postgis' or 'haversine_fallback'")
    emergency_only_filter: bool
    hospitals: List[NearbyHospitalItem] = Field(default_factory=list)
    advisory_notes: List[str] = Field(default_factory=list)
    emergency_helplines_india: Dict[str, str] = Field(
        default_factory=lambda: {
            "National Emergency Number": "112",
            "Ambulance / Medical Emergency": "108",
            "Police Emergency": "100",
            "Traffic Police Helpline": "103",
        }
    )
    disclaimer: str = (
        "EMERGENCY NOTICE: Distances shown are straight-line geometric approximations and DO NOT "
        "reflect road driving distance, traffic congestion, or emergency vehicle ETA. "
        "Facility capacities are static reference benchmarks, NOT live bed telemetry. "
        "For acute trauma or life-threatening emergencies in India, dial 112 or 108 immediately."
    )
