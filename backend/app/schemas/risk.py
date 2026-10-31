"""Pydantic schemas for Accident-Risk Prediction and Dataset Pipeline.

Ensures strict typing, coordinate bounds validation, transparent status
reporting, and explicit distinction between calibrated model outputs vs.
unavailable-model states.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict, field_validator


ALLOWED_ROAD_CLASSIFICATIONS = {
    "national_highway",
    "state_highway",
    "major_district_road",
    "urban_arterial",
    "rural_road",
    "other",
}

ALLOWED_SURFACE_CONDITIONS = {
    "dry",
    "wet",
    "waterlogged",
    "unpaved",
    "loose_gravel",
}

ALLOWED_LIGHTING_CONDITIONS = {
    "daylight",
    "dawn_dusk",
    "night_lit",
    "night_unlit",
}

ALLOWED_WEATHER_CONDITIONS = {
    "clear",
    "rain",
    "fog",
    "haze",
    "heavy_wind",
}


class RiskPredictionRequest(BaseModel):
    """Input payload for road-segment accident risk prediction."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    road_classification: str = Field(
        default="urban_arterial",
        description="Road category: national_highway, state_highway, major_district_road, urban_arterial, rural_road, other"
    )
    speed_limit_kmh: float = Field(
        default=50.0,
        ge=10.0,
        le=160.0,
        description="Corridor posted speed limit in km/h"
    )
    surface_condition: str = Field(
        default="dry",
        description="Road surface condition: dry, wet, waterlogged, unpaved, loose_gravel"
    )
    lighting_condition: str = Field(
        default="daylight",
        description="Lighting condition: daylight, dawn_dusk, night_lit, night_unlit"
    )
    weather_condition: str = Field(
        default="clear",
        description="Current or forecasted weather: clear, rain, fog, haze, heavy_wind"
    )
    search_radius_meters: float = Field(
        default=1000.0,
        ge=50.0,
        le=10000.0,
        description="Radius in meters to query nearby hazard density from PostGIS (default 1000m)"
    )
    vehicle_safety_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional vehicle safety assessment score (from Phase 4 vehicle index)"
    )

    @field_validator("road_classification")
    @classmethod
    def validate_road_class(cls, v: str) -> str:
        norm = v.strip().lower()
        if norm not in ALLOWED_ROAD_CLASSIFICATIONS:
            raise ValueError(f"road_classification must be one of {sorted(ALLOWED_ROAD_CLASSIFICATIONS)} (got '{v}')")
        return norm

    @field_validator("surface_condition")
    @classmethod
    def validate_surface(cls, v: str) -> str:
        norm = v.strip().lower()
        if norm not in ALLOWED_SURFACE_CONDITIONS:
            raise ValueError(f"surface_condition must be one of {sorted(ALLOWED_SURFACE_CONDITIONS)} (got '{v}')")
        return norm

    @field_validator("lighting_condition")
    @classmethod
    def validate_lighting(cls, v: str) -> str:
        norm = v.strip().lower()
        if norm not in ALLOWED_LIGHTING_CONDITIONS:
            raise ValueError(f"lighting_condition must be one of {sorted(ALLOWED_LIGHTING_CONDITIONS)} (got '{v}')")
        return norm

    @field_validator("weather_condition")
    @classmethod
    def validate_weather(cls, v: str) -> str:
        norm = v.strip().lower()
        if norm not in ALLOWED_WEATHER_CONDITIONS:
            raise ValueError(f"weather_condition must be one of {sorted(ALLOWED_WEATHER_CONDITIONS)} (got '{v}')")
        return norm


class FeatureContribution(BaseModel):
    """Individual feature attribution from TreeSHAP or feature importance analysis."""
    feature_name: str
    feature_value: Any
    attribution_value: float = Field(..., description="Directional impact on risk score (positive increases risk, negative decreases)")
    direction: str = Field(..., description="'increases_risk' or 'decreases_risk'")
    description: str


class RiskModelStatusResponse(BaseModel):
    """Operational status and provenance metadata for the accident risk model."""
    available: bool = Field(..., description="True only if trained model artifact exists and passed validation")
    status: str = Field(..., description="MODEL_AVAILABLE, MODEL_UNAVAILABLE, or TRAINING_DATA_UNAVAILABLE")
    model_version: Optional[str] = None
    model_architecture: str = "XGBoost Classifier + TreeSHAP"
    dataset_provenance: str = "Awaiting verified historical road accident records"
    training_date: Optional[str] = None
    evaluation_metrics: Optional[Dict[str, Any]] = None
    details: str
    features_expected: List[str]
    missing_dependencies: List[str] = Field(default_factory=list)


class RiskPredictionResponse(BaseModel):
    """Output schema for accident risk prediction."""
    model_config = ConfigDict(from_attributes=True)

    prediction_id: UUID = Field(default_factory=uuid4)
    status: str = Field(..., description="'success' or 'model_unavailable'")
    risk_tier: str = Field(..., description="'Low', 'Medium', 'High', 'Critical', or 'Unavailable'")
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Predicted risk index (0.0 to 100.0) if model available")
    risk_score_interpretation: str
    model_version: str
    corridor_coordinates: Dict[str, float]
    spatial_hazard_density: Dict[str, Any]
    features_used: Dict[str, Any]
    feature_contributions: List[FeatureContribution] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    disclaimer: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetValidationReport(BaseModel):
    """Audit report from dataset schema and quality inspection."""
    is_valid: bool
    total_records: int
    feature_columns: List[str]
    target_column: Optional[str] = None
    missing_values_by_column: Dict[str, int] = Field(default_factory=dict)
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    dataset_provenance_notes: str
