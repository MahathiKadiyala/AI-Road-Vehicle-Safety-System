"""Accident-Risk Prediction API Endpoints — Phase 5.2.

Provides road-segment accident risk inference, model status diagnostics,
and seamless integration with Phase 5.1 PostGIS hazard density.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.spatial import spatial_service
from app.ml.risk.predictor import risk_predictor, ModelUnavailableError
from app.schemas.risk import (
    RiskModelStatusResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
)

logger = logging.getLogger("roadsafety.api.risk")

router = APIRouter(prefix="/risk", tags=["Accident Risk Prediction"])


@router.get(
    "/status",
    response_model=RiskModelStatusResponse,
    summary="Get Accident-Risk Model Status & Data Provenance",
)
async def get_risk_model_status():
    """Retrieve operational status, training state, and required data schema of the risk model."""
    return risk_predictor.get_status()


@router.post(
    "/predict",
    response_model=RiskPredictionResponse,
    summary="Predict road-segment accident risk index (Advisory AI)",
)
async def predict_accident_risk(
    request: RiskPredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Predict road-segment accident risk for given corridor parameters and coordinates.

    Synthesizes:
    1. Spatial hazard density from Phase 5.1 PostGIS service within the specified radius.
    2. Environmental conditions (weather, surface, lighting, speed limit).
    3. Optional vehicle safety index from Phase 4.

    If the ML model is not yet trained with genuine accident data, returns HTTP 503
    (MODEL_UNAVAILABLE) to ensure unverified or deceptive scores are never presented.
    """
    # 1. Fetch real nearby hazard density using Phase 5.1 PostGIS spatial service
    try:
        density_data = await spatial_service.query_hazard_density(
            db=db,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.search_radius_meters,
        )
        density_summary = density_data.model_dump()
    except Exception as exc:
        logger.warning(f"Could not fetch spatial hazard density: {exc}")
        density_summary = {
            "total_hazards": 0,
            "density_per_sqkm": 0.0,
            "note": f"Spatial query unavailable: {exc}",
        }

    # 2. Check model availability
    status_info = risk_predictor.get_status()
    if not status_info.available:
        logger.info(f"Risk prediction rejected: {status_info.details}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MODEL_UNAVAILABLE",
                "status": status_info.status,
                "message": status_info.details,
                "dataset_provenance": status_info.dataset_provenance,
                "spatial_hazard_density": density_summary,
            },
        )

    # 3. Perform prediction if model is available
    try:
        prediction = await risk_predictor.predict_async(request, density_summary)
        return prediction
    except ModelUnavailableError as m_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MODEL_UNAVAILABLE",
                "message": str(m_err),
            },
        )
    except Exception as exc:
        logger.error(f"Inference error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk prediction failed due to an internal server error.",
        )
