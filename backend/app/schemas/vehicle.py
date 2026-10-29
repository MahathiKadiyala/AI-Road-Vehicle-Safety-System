"""Pydantic schemas for Vehicle Safety Assessment (Phase 4)."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ParameterAuditItem(BaseModel):
    """Structured audit item for an individual vehicle parameter."""
    parameter: str
    measured_value: Any
    status: str = Field(..., description="'compliant', 'warning', 'violation', or 'unverified'")
    is_statutory: bool = Field(..., description="True if governed by Indian statutory law (e.g. CMVR)")
    statutory_reference: str = Field(..., description="Authoritative standard citation (e.g. CMVR Rule 95 / AIS-044)")
    finding: str = Field(..., description="Concise explanation of finding")
    recommendation: str = Field(..., description="Actionable recommendation for owner/buyer")
    deduction_applied: float = Field(..., ge=0.0, description="Score deduction applied for this parameter")


class VehicleAssessmentCreate(BaseModel):
    """Input payload for preliminary vehicle evaluation."""
    make: str = Field(..., max_length=80, json_schema_extra={"example": "Maruti Suzuki"})
    model: str = Field(..., max_length=80, json_schema_extra={"example": "Swift"})
    year: int = Field(..., ge=1970, le=2030, json_schema_extra={"example": 2018})
    odometer_km: float = Field(..., ge=0, json_schema_extra={"example": 52000.0})
    vehicle_category: Optional[str] = Field(
        default=None,
        description="Vehicle classification under CMVR: 'M1_passenger_car' (min 1.6mm tyre), 'L_two_three_wheeler' (min 0.8mm tyre), 'commercial_transport', or 'unknown'",
        json_schema_extra={"example": "M1_passenger_car"}
    )
    brake_pad_thickness_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=25.0,
        description="Measured brake pad friction material thickness in mm (Advisory OEM discard threshold is 2.0 mm)",
        json_schema_extra={"example": 4.5}
    )
    tyre_tread_depth_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=20.0,
        description="Measured tyre non-skid tread depth in mm (CMVR Rule 95 limit: 1.6 mm for M1, 0.8 mm for L)",
        json_schema_extra={"example": 3.2}
    )
    service_records_count: int = Field(default=0, ge=0)
    past_accidents_count: int = Field(default=0, ge=0)
    puc_valid: Optional[bool] = Field(
        default=None,
        description="Optional: Whether Pollution Under Control (PUC) certificate is active (Self-Reported)"
    )
    insurance_valid: Optional[bool] = Field(
        default=None,
        description="Optional: Whether mandatory motor third-party insurance is active (Self-Reported)"
    )
    fitness_certificate_valid: Optional[bool] = Field(
        default=None,
        description="Optional: Whether fitness/registration renewal is verified (for vehicle age >= 15 or commercial)"
    )
    disclaimer_acknowledged: bool = Field(
        ...,
        description="User must acknowledge this is a preliminary estimate, not a certified physical inspection."
    )


class VehicleAssessmentRead(VehicleAssessmentCreate):
    """Output schema for preliminary vehicle evaluation results."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preliminary_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: str = Field(..., description="'Low', 'Moderate', 'High', or 'Critical'")
    vehicle_category: str = Field(default="M1_passenger_car")
    critical_warnings: List[str] = Field(default_factory=list)
    statutory_violations: List[str] = Field(default_factory=list)
    advisory_warnings: List[str] = Field(default_factory=list)
    parameter_breakdown: List[ParameterAuditItem] = Field(default_factory=list)
    missing_unverified_attributes: List[str] = Field(default_factory=list)
    data_completeness: str = Field(default="Standard", description="'Comprehensive', 'Standard', or 'Minimal'")
    document_verification_source: str = Field(default="self_reported_unverified")
    disclaimer_text: str = Field(default="")
    legal_disclaimer_version: str = Field(default="CMVR-AIS-Advisory-v2.0")
    created_at: datetime


class VehicleStandardsResponse(BaseModel):
    """Authoritative Indian legal and technical standards registry response."""
    standards: Dict[str, Any]
    disclaimer: str
    version: str
