"""Road-Damage Detection API endpoints — Phase 3 (YOLO).

Provides automated road distress inference for uploaded images, returning structured
detections, bounding boxes, advisory severity recommendations, and rendered visualizations.
"""
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.storage import validate_and_save_image, delete_image_file
from app.ml.detector import detector_service, ModelUnavailableError
from app.schemas.damage_detection import (
    DamageDetectionResponse,
    DamageModelStatusResponse,
)

logger = logging.getLogger("roadsafety.api.damage")

router = APIRouter(prefix="/damage", tags=["Road Distress Detection"])


@router.get(
    "/status",
    response_model=DamageModelStatusResponse,
    summary="Get Road-Damage YOLO model status and availability",
)
async def get_damage_model_status():
    """Retrieve operational status, weights file presence, and target classes of the YOLO model."""
    return detector_service.get_status()


@router.post(
    "/detect",
    response_model=DamageDetectionResponse,
    summary="Detect road distress in uploaded image (Advisory AI)",
)
async def detect_road_damage(
    image: UploadFile = File(..., description="Road surface photo (JPEG/PNG/WebP, max 10MB)"),
    confidence_threshold: Optional[float] = Form(
        default=None,
        ge=0.05,
        le=0.95,
        description="Optional minimum confidence score threshold (default 0.25)",
    ),
):
    """Analyze a road surface image for distress: cracks (D00, D10, D20) and potholes (D40).

    Uses a fine-tuned YOLO model. Processing is offloaded to a background worker thread
    to ensure the asynchronous FastAPI event loop is never blocked.
    """
    # 1. Fast model availability check
    status_info = detector_service.get_status()
    if not status_info.available:
        logger.warning(f"Detection request rejected: {status_info.details}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MODEL_UNAVAILABLE",
                "message": (
                    "Road damage detection model weights are not loaded. "
                    "Trained road_damage_yolo.pt weights must be present in backend/app/ml/artifacts/."
                ),
                "details": status_info.details,
            },
        )

    # 2. Content-based image validation and secure saving (reusing core storage)
    if not image or not image.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in upload request.",
        )

    saved_abs_path: Optional[str] = None
    try:
        _, saved_abs_path = await validate_and_save_image(image)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image upload validation failed: {str(val_err)}",
        )

    # 3. Perform inference via thread offload (non-blocking)
    try:
        detection_result = await detector_service.detect_async(
            image_path=saved_abs_path,
            confidence_threshold=confidence_threshold,
        )
        return detection_result

    except ModelUnavailableError as model_err:
        logger.error(f"Model unavailable during inference: {model_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MODEL_UNAVAILABLE",
                "message": str(model_err),
            },
        )
    except ValueError as img_err:
        logger.warning(f"Malformed image error: {img_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image: {str(img_err)}",
        )
    except Exception as exc:
        logger.error(f"Unexpected inference failure: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during neural network inference.",
        )
    finally:
        # Note: We retain the saved image or clean up if needed.
        pass
