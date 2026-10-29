"""Hospital & Emergency Response API endpoints — Phase 5.3.

Provides spatial proximity lookup for nearby verified hospitals and trauma centers,
with straight-line distance approximations, facility reference details, and official
emergency helpline advisories.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.spatial import spatial_service, SpatialServiceUnavailableError, SpatialServiceError
from app.models.hospital import Hospital
from app.schemas.hospital import HospitalRead, NearbyHospitalsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hospitals", tags=["Hospitals & Emergency Response"])


@router.get(
    "/nearby",
    response_model=NearbyHospitalsResponse,
    summary="Find nearby verified hospitals and trauma centers within a radius",
)
async def get_nearby_hospitals(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="WGS84 Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="WGS84 Longitude (-180 to 180)"),
    radius_meters: float = Query(
        10000.0,
        ge=100.0,
        le=100000.0,
        description="Search radius in meters (100 to 100,000, default 10,000)",
    ),
    emergency_only: bool = Query(
        False,
        description="Filter for facilities operating 24/7 emergency casualty triage",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum facilities to return (1 to 100, default 20)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Query verified hospitals and trauma centers within a radius.

    Evaluates spatial proximity using PostGIS ST_DWithin with Geography casting in meters,
    with an exact Haversine great-circle calculation fallback.

    Results are ordered by straight-line distance ascending.
    Notice: Distances are straight-line geometric approximations and do NOT reflect road
    navigation distance or emergency dispatch ETAs.
    """
    try:
        response = await spatial_service.query_nearby_hospitals(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            emergency_only=emergency_only,
            limit=limit,
        )
        return response
    except SpatialServiceUnavailableError as srv_err:
        logger.error(f"Spatial hospital service unavailable: {srv_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Hospital proximity service unavailable: {str(srv_err)}",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error querying nearby hospitals: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to query nearby hospitals. Database or spatial engine may be unavailable.",
        )


@router.get(
    "/{hospital_id}",
    response_model=HospitalRead,
    summary="Retrieve reference details for a specific hospital by ID",
)
async def get_hospital_by_id(
    hospital_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a single hospital or trauma facility by its UUID."""
    try:
        result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
        hospital = result.scalar_one_or_none()

        if hospital is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hospital facility with id '{hospital_id}' not found.",
            )

        return hospital
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Database error retrieving hospital {hospital_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve hospital record. Database may be unavailable.",
        )
