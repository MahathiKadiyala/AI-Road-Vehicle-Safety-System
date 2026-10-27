"""Pydantic schemas for Road Distress & Damage Detection (Phase 3 YOLO)."""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 to 1.0) and pixel values."""
    xmin: float = Field(..., ge=0.0, le=1.0, description="Normalized minimum X")
    ymin: float = Field(..., ge=0.0, le=1.0, description="Normalized minimum Y")
    xmax: float = Field(..., ge=0.0, le=1.0, description="Normalized maximum X")
    ymax: float = Field(..., ge=0.0, le=1.0, description="Normalized maximum Y")
    width: float = Field(..., ge=0.0, le=1.0, description="Normalized width")
    height: float = Field(..., ge=0.0, le=1.0, description="Normalized height")
    pixel_box: Optional[List[int]] = Field(
        default=None,
        description="Optional absolute pixel coordinates [x1, y1, x2, y2]"
    )


class DamageDetectionItem(BaseModel):
    """Structured detection item for road distress."""
    class_id: int = Field(..., ge=0, le=3, description="Zero-indexed class ID (0-3)")
    class_code: str = Field(..., description="RDD class code: D00, D10, D20, or D40")
    class_name: str = Field(..., description="Human-readable distress classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    box: BoundingBox = Field(..., description="Bounding box location")
    suggested_hazard_type: str = Field(
        ...,
        description="Mapped hazard category for citizen reporting ('crack' or 'pothole')"
    )
    suggested_severity: str = Field(
        ...,
        description="Suggested triage severity ('low', 'medium', 'high', 'critical')"
    )


class DamageDetectionResponse(BaseModel):
    """Full API response for image-based damage inference."""
    success: bool = Field(default=True, description="Whether detection succeeded")
    model_name: str = Field(default="YOLO-RoadDamage", description="Model architecture/name")
    model_version: Optional[str] = Field(default="1.0.0", description="Model training version")
    device: str = Field(default="cpu", description="Execution device (e.g. cpu, cuda)")
    detections_count: int = Field(..., ge=0, description="Total number of distress items detected")
    detections: List[DamageDetectionItem] = Field(default_factory=list, description="List of detected damages")
    inference_time_ms: float = Field(..., ge=0.0, description="Inference latency in milliseconds")
    image_width: int = Field(..., ge=1, description="Original image width in pixels")
    image_height: int = Field(..., ge=1, description="Original image height in pixels")
    annotated_image_url: Optional[str] = Field(
        default=None,
        description="URL of rendered image with bounding boxes"
    )
    disclaimer: str = Field(
        default=(
            "ADVISORY NOTICE: AI-generated road distress detection is provided for informational "
            "and triage assistance only. It does not constitute an official road audit, engineering certification, "
            "or guarantee of road surface safety."
        ),
        description="Mandatory advisory disclaimer"
    )


class DamageModelStatusResponse(BaseModel):
    """Model availability and diagnostics status response."""
    available: bool = Field(..., description="Whether model weights are loaded and ready")
    model_name: str = Field(..., description="Model descriptor")
    model_path: str = Field(..., description="Configured path to weights file")
    weights_present: bool = Field(..., description="Whether weight file exists on disk")
    device: str = Field(..., description="Execution compute device")
    supported_classes: Dict[str, str] = Field(..., description="Target class code and description mapping")
    details: Optional[str] = Field(default=None, description="Additional status or setup instructions")
