"""Vehicle Safety Assessment API Endpoints — Phase 4.

Provides rule-based, explainable vehicle evaluations against Indian technical
and statutory standards (CMVR 1989 & AIS).
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.vehicle_rules import (
    evaluate_vehicle_safety,
    STANDARDS_REGISTRY,
    MANDATORY_DISCLAIMER_TEXT,
    LEGAL_DISCLAIMER_VERSION,
)
from app.models.vehicle import VehicleAssessment
from app.schemas.vehicle import (
    VehicleAssessmentCreate,
    VehicleAssessmentRead,
    VehicleStandardsResponse,
    ParameterAuditItem,
)

logger = logging.getLogger("roadsafety.api.vehicles")

router = APIRouter(prefix="/vehicles", tags=["Vehicle Safety Assessment"])


@router.get(
    "/standards",
    response_model=VehicleStandardsResponse,
    summary="Get authoritative Indian vehicle legal & technical standards",
)
async def get_vehicle_standards():
    """Retrieve authoritative Indian regulatory references (CMVR 1989 Rules 95, 96, 115, 52/62, MVA 1988).

    Ensures zero black-box opacity by allowing clients to inspect all thresholds and statutory citations.
    """
    return VehicleStandardsResponse(
        standards=STANDARDS_REGISTRY,
        disclaimer=MANDATORY_DISCLAIMER_TEXT,
        version=LEGAL_DISCLAIMER_VERSION,
    )


@router.post(
    "/assess",
    response_model=VehicleAssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate vehicle safety condition under Indian standards (CMVR 95 / AIS)",
)
async def assess_vehicle_safety(
    payload: VehicleAssessmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Run an explainable preliminary assessment on vehicle condition.

    Evaluates:
      1. Category-specific Tyre Non-Skid Depth against statutory limits (CMVR Rule 95(3)(iv) / AIS-044)
      2. Disc Brake Pad Thickness against OEM advisory discard limit
      3. Duty cycle and annual mileage wear patterns
      4. Accident history and structural risk
      5. Periodic service documentation completeness
      6. Self-reported statutory document status (PUC, Insurance, Registration renewal)

    Requires explicit disclaimer acknowledgement.
    """
    # 1. Enforce disclaimer acknowledgement
    if not payload.disclaimer_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail=(
                "Assessment requires explicit acknowledgement that results are preliminary "
                "engineering estimates and do not certify legal roadworthiness or replace physical inspection."
            ),
        )

    # 2. Run deterministic rule evaluation
    try:
        eval_result = evaluate_vehicle_safety(
            make=payload.make,
            model=payload.model,
            year=payload.year,
            odometer_km=payload.odometer_km,
            brake_pad_thickness_mm=payload.brake_pad_thickness_mm,
            tyre_tread_depth_mm=payload.tyre_tread_depth_mm,
            vehicle_category=payload.vehicle_category,
            service_records_count=payload.service_records_count,
            past_accidents_count=payload.past_accidents_count,
            puc_valid=payload.puc_valid,
            insurance_valid=payload.insurance_valid,
            fitness_certificate_valid=payload.fitness_certificate_valid,
        )
    except Exception as eval_err:
        logger.error(f"Error executing vehicle safety evaluation: {eval_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute vehicle safety evaluation.",
        )

    # 3. Persist assessment record to database
    assessment_record = VehicleAssessment(
        make=payload.make.strip(),
        model=payload.model.strip(),
        year=payload.year,
        odometer_km=payload.odometer_km,
        brake_pad_thickness_mm=payload.brake_pad_thickness_mm,
        tyre_tread_depth_mm=payload.tyre_tread_depth_mm,
        service_records_count=payload.service_records_count,
        past_accidents_count=payload.past_accidents_count,
        preliminary_score=eval_result.preliminary_score,
        risk_tier=eval_result.risk_tier,
        critical_warnings=eval_result.critical_warnings,
        assessment_details={
            "vehicle_category": eval_result.vehicle_category,
            "statutory_violations": eval_result.statutory_violations,
            "advisory_warnings": eval_result.advisory_warnings,
            "parameter_breakdown": eval_result.parameter_breakdown,
            "missing_unverified_attributes": eval_result.missing_unverified_attributes,
            "data_completeness": eval_result.data_completeness,
            "document_verification_source": eval_result.document_verification_source,
            "puc_valid": payload.puc_valid,
            "insurance_valid": payload.insurance_valid,
            "fitness_certificate_valid": payload.fitness_certificate_valid,
        },
        legal_disclaimer_version=eval_result.legal_disclaimer_version,
        disclaimer_acknowledged=True,
    )

    try:
        db.add(assessment_record)
        await db.commit()
        await db.refresh(assessment_record)
        logger.info(
            f"Vehicle assessment created: id={assessment_record.id}, "
            f"category={eval_result.vehicle_category}, "
            f"vehicle='{payload.year} {payload.make} {payload.model}', "
            f"score={eval_result.preliminary_score}, tier={eval_result.risk_tier}"
        )
    except Exception as db_exc:
        await db.rollback()
        logger.error(f"Database error saving vehicle assessment: {db_exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to save vehicle assessment. Database may be unavailable.",
        )

    # 4. Construct rich response schema
    return VehicleAssessmentRead(
        id=assessment_record.id,
        make=assessment_record.make,
        model=assessment_record.model,
        year=assessment_record.year,
        odometer_km=assessment_record.odometer_km,
        vehicle_category=eval_result.vehicle_category,
        brake_pad_thickness_mm=assessment_record.brake_pad_thickness_mm,
        tyre_tread_depth_mm=assessment_record.tyre_tread_depth_mm,
        service_records_count=assessment_record.service_records_count,
        past_accidents_count=assessment_record.past_accidents_count,
        puc_valid=payload.puc_valid,
        insurance_valid=payload.insurance_valid,
        fitness_certificate_valid=payload.fitness_certificate_valid,
        disclaimer_acknowledged=True,
        preliminary_score=assessment_record.preliminary_score,
        risk_tier=assessment_record.risk_tier,
        critical_warnings=assessment_record.critical_warnings,
        statutory_violations=eval_result.statutory_violations,
        advisory_warnings=eval_result.advisory_warnings,
        parameter_breakdown=[ParameterAuditItem(**item) for item in eval_result.parameter_breakdown],
        missing_unverified_attributes=eval_result.missing_unverified_attributes,
        data_completeness=eval_result.data_completeness,
        document_verification_source=eval_result.document_verification_source,
        disclaimer_text=eval_result.disclaimer_text,
        legal_disclaimer_version=assessment_record.legal_disclaimer_version,
        created_at=assessment_record.created_at,
    )


@router.get(
    "/{assessment_id}",
    response_model=VehicleAssessmentRead,
    summary="Retrieve a vehicle assessment by ID",
)
async def get_vehicle_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an existing vehicle assessment by its UUID."""
    try:
        result = await db.execute(
            select(VehicleAssessment).where(VehicleAssessment.id == assessment_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle assessment with ID '{assessment_id}' not found.",
            )

        details = record.assessment_details or {}
        raw_breakdown = details.get("parameter_breakdown", [])

        return VehicleAssessmentRead(
            id=record.id,
            make=record.make,
            model=record.model,
            year=record.year,
            odometer_km=record.odometer_km,
            vehicle_category=details.get("vehicle_category", "unknown"),
            brake_pad_thickness_mm=record.brake_pad_thickness_mm,
            tyre_tread_depth_mm=record.tyre_tread_depth_mm,
            service_records_count=record.service_records_count,
            past_accidents_count=record.past_accidents_count,
            puc_valid=details.get("puc_valid"),
            insurance_valid=details.get("insurance_valid"),
            fitness_certificate_valid=details.get("fitness_certificate_valid"),
            disclaimer_acknowledged=record.disclaimer_acknowledged,
            preliminary_score=record.preliminary_score,
            risk_tier=record.risk_tier,
            critical_warnings=record.critical_warnings,
            statutory_violations=details.get("statutory_violations", []),
            advisory_warnings=details.get("advisory_warnings", []),
            parameter_breakdown=[ParameterAuditItem(**item) for item in raw_breakdown],
            missing_unverified_attributes=details.get("missing_unverified_attributes", []),
            data_completeness=details.get("data_completeness", "Standard"),
            document_verification_source=details.get("document_verification_source", "self_reported_unverified"),
            disclaimer_text=MANDATORY_DISCLAIMER_TEXT,
            legal_disclaimer_version=record.legal_disclaimer_version,
            created_at=record.created_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error retrieving vehicle assessment {assessment_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve vehicle assessment. Database may be unavailable.",
        )
