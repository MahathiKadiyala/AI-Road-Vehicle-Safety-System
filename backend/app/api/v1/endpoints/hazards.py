"""Hazard Reporting API endpoints — Phase 2.

Provides CRUD operations for citizen-submitted road hazard reports.
All hazard classifications are labeled as user reports (not AI-verified detections).
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.storage import validate_and_save_image, get_image_url, delete_image_file
from app.core.spatial import create_point_geometry, spatial_service, SpatialServiceUnavailableError
from app.models.hazard import Hazard
from app.schemas.hazard import HazardRead, HazardDensityResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hazards", tags=["Hazard Reports"])

# Valid enums (must match Pydantic schema validators)
ALLOWED_HAZARD_TYPES = {"pothole", "crack", "debris", "waterlogging", "obstacle", "other"}
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}
ALLOWED_STATUSES = {"reported", "verified", "in_progress", "resolved", "dismissed"}


@router.post(
    "",
    response_model=HazardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new hazard report (user-submitted, not AI-verified)",
)
async def create_hazard_report(
    title: str = Form(..., max_length=150, description="Short title of the hazard"),
    latitude: float = Form(..., description="WGS84 Latitude (-90 to 90)"),
    longitude: float = Form(..., description="WGS84 Longitude (-180 to 180)"),
    hazard_type: str = Form(default="pothole", description="pothole, crack, debris, waterlogging, obstacle, other"),
    severity: str = Form(default="medium", description="low, medium, high, critical"),
    description: Optional[str] = Form(default=None, description="Detailed hazard context"),
    image: Optional[UploadFile] = File(default=None, description="Optional photo evidence (JPEG/PNG/WebP, max 10 MB)"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new citizen-reported road hazard.

    The report is labeled as a **user-submitted citizen report** — not an
    AI-verified detection. Image uploads are validated by content inspection.
    """
    # --- Field validation ---
    errors = []

    if not title or not title.strip():
        errors.append("title: This field is required and cannot be blank.")

    if latitude < -90.0 or latitude > 90.0:
        errors.append(f"latitude: Must be between -90 and 90 (got {latitude}).")

    if longitude < -180.0 or longitude > 180.0:
        errors.append(f"longitude: Must be between -180 and 180 (got {longitude}).")

    hazard_type_lower = hazard_type.strip().lower()
    if hazard_type_lower not in ALLOWED_HAZARD_TYPES:
        errors.append(
            f"hazard_type: Must be one of {sorted(ALLOWED_HAZARD_TYPES)} (got '{hazard_type}')."
        )

    severity_lower = severity.strip().lower()
    if severity_lower not in ALLOWED_SEVERITIES:
        errors.append(
            f"severity: Must be one of {sorted(ALLOWED_SEVERITIES)} (got '{severity}')."
        )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors,
        )

    # --- Image handling ---
    image_path: Optional[str] = None
    saved_abs_path: Optional[str] = None
    if image and image.filename:
        try:
            relative_path, abs_path = await validate_and_save_image(image)
            image_path = relative_path
            saved_abs_path = abs_path
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image upload failed: {str(e)}",
            )

    # --- Build PostGIS Point geometry (SRID 4326: X=longitude, Y=latitude) ---
    point_geom = create_point_geometry(latitude=latitude, longitude=longitude)

    # --- Persist to database ---
    try:
        new_hazard = Hazard(
            title=title.strip(),
            description=description.strip() if description else None,
            hazard_type=hazard_type_lower,
            severity=severity_lower,
            latitude=latitude,
            longitude=longitude,
            geom=point_geom,
            image_path=image_path,
            source="citizen_report",
            status="reported",
        )
        db.add(new_hazard)
        await db.commit()
        await db.refresh(new_hazard)

        logger.info(f"Hazard report created: id={new_hazard.id}, type={hazard_type_lower}")
        return new_hazard

    except Exception as exc:
        await db.rollback()
        if saved_abs_path:
            delete_image_file(saved_abs_path)
        logger.error(f"Database error creating hazard report: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to save hazard report. Database may be unavailable.",
        )


@router.get(
    "",
    response_model=list[HazardRead],
    summary="List hazard reports with optional filtering",
)
async def list_hazard_reports(
    hazard_type: Optional[str] = Query(default=None, description="Filter by hazard type"),
    severity: Optional[str] = Query(default=None, description="Filter by severity level"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by report status"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve hazard reports with optional filtering by type, severity, and status.

    Reports are ordered by creation date (newest first).
    """
    try:
        query = select(Hazard)

        # Apply optional filters
        if hazard_type:
            ht = hazard_type.strip().lower()
            if ht not in ALLOWED_HAZARD_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid hazard_type filter. Allowed: {sorted(ALLOWED_HAZARD_TYPES)}",
                )
            query = query.where(Hazard.hazard_type == ht)

        if severity:
            sv = severity.strip().lower()
            if sv not in ALLOWED_SEVERITIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity filter. Allowed: {sorted(ALLOWED_SEVERITIES)}",
                )
            query = query.where(Hazard.severity == sv)

        if status_filter:
            sf = status_filter.strip().lower()
            if sf not in ALLOWED_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter. Allowed: {sorted(ALLOWED_STATUSES)}",
                )
            query = query.where(Hazard.status == sf)

        query = query.order_by(Hazard.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        hazards = result.scalars().all()
        return hazards

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Database error listing hazard reports: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve hazard reports. Database may be unavailable.",
        )


@router.get(
    "/density",
    response_model=HazardDensityResponse,
    summary="Compute nearby hazard density within a specified radius",
)
async def get_hazard_density(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center WGS84 Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center WGS84 Longitude (-180 to 180)"),
    radius_meters: float = Query(
        default=1000.0,
        ge=10.0,
        le=50000.0,
        description="Search radius in meters (10m to 50,000m)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Calculate nearby hazard counts, breakdowns, and density for given coordinates.

    Executes PostGIS ST_DWithin with meter-based Geography casting.
    Falls back gracefully to Haversine bounding-box calculation when PostGIS is not available.
    """
    try:
        return await spatial_service.query_hazard_density(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        )
    except SpatialServiceUnavailableError as srv_err:
        logger.error(f"Spatial service unavailable: {srv_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spatial density service is temporarily unavailable. Database or spatial engine may be offline.",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error computing hazard density: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to compute hazard density. Database may be unavailable.",
        )


@router.get(
    "/{hazard_id}",
    response_model=HazardRead,
    summary="Retrieve a specific hazard report by ID",
)
async def get_hazard_report(
    hazard_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single hazard report by its UUID."""
    try:
        result = await db.execute(select(Hazard).where(Hazard.id == hazard_id))
        hazard = result.scalar_one_or_none()

        if hazard is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hazard report with id '{hazard_id}' not found.",
            )

        return hazard

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Database error retrieving hazard report {hazard_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve hazard report. Database may be unavailable.",
        )
