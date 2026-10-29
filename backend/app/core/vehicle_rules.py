"""Vehicle Safety Assessment Engine — Phase 4.

Provides transparent, deterministic, rule-based vehicle safety evaluations based on
authoritative Indian legal standards and automotive engineering guidelines:
  - CMVR 1989 Rule 95(3)(iv): Non-skid depth (NSD) / Tread Wear Indicators (TWI)
    differentiated by vehicle category (M/N vs L).
  - AIS-044 (Parts 1 to 3) / AIS-050: Pneumatic tyres specifications and TWI marking.
  - Manufacturer / OEM Service Guidelines (under CMVR Rule 96 braking safety):
    Brake pad friction wear discard limits (Advisory, not statutory).
  - CMVR 1989 Rule 115(7): Pollution Under Control (PUC) certification.
  - MVA 1988 Section 146: Mandatory Third-Party Insurance.
  - MVA 1988 Sections 41 & 56 / CMVR 1989 Rules 52 & 62: Registration validity
    and 15-year renewal for private non-transport vs commercial transport fitness.

Strictly separates statutory legal non-compliance from advisory maintenance guidelines.
Does not claim or certify roadworthiness or RTO fitness.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any


class VehicleCategory(str, Enum):
    """Vehicle categories recognized under Central Motor Vehicles Rules (CMVR)."""
    M1_PASSENGER_CAR = "M1_passenger_car"      # Motor vehicles with at least 4 wheels used for carrying passengers (up to 8 seats)
    L_TWO_THREE_WHEELER = "L_two_three_wheeler"  # 2-wheelers, 3-wheelers, quadricycles, e-rickshaws, e-carts
    COMMERCIAL_TRANSPORT = "commercial_transport" # Transport / goods / public service vehicles
    UNKNOWN = "unknown"                          # Category not provided by user


# ── Authoritative Indian Regulatory Standards Registry ───────────────────────

STANDARDS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "cmvr_rule_95": {
        "title": "Central Motor Vehicles Rules (CMVR) 1989 — Rule 95(3)(iv)",
        "legal_citation": "CMVR 1989, Rule 95, Sub-rule (3), Clause (iv)",
        "authority": "Ministry of Road Transport and Highways (MoRTH), Government of India",
        "official_source_url": "https://morth.nic.in/central-motor-vehicles-rules-1989",
        "scope": "Size and Ply Rating of Tyres; Non-Skid Depth (NSD) and Tread Wear Indicators (TWI)",
        "category": "Statutory Indian Law (Non-Negotiable)",
        "thresholds": {
            "M1_passenger_car": {
                "statutory_minimum_nsd_mm": 1.6,
                "advisory_replacement_mm": 2.5,
                "description": "Four-wheeled passenger cars and commercial vehicles (Categories M & N)."
            },
            "L_two_three_wheeler": {
                "statutory_minimum_nsd_mm": 0.8,
                "advisory_replacement_mm": 1.5,
                "description": "Two-wheelers, three-wheelers, quadricycles, e-rickshaws, e-carts (Category L)."
            },
        },
        "legal_wording": (
            "Every tyre shall have a tread pattern groove depth of not less than 0.8 mm in the case "
            "of two-wheelers and three-wheelers and not less than 1.6 mm in the case of other motor vehicles "
            "across the entire breadth of the tread and throughout the entire circumference of the tyre or "
            "the tyre tread wear indicator (TWI) is not reached."
        ),
        "legal_consequence": (
            "Operating a vehicle below the statutory NSD threshold is an offense under Section 177 / 190 "
            "of the Motor Vehicles Act, 1988."
        ),
    },
    "ais_044": {
        "title": "Automotive Industry Standard AIS-044 (Parts 1–3) & AIS-050",
        "legal_citation": "AIS-044 / AIS-050 notified under CMVR Rule 126",
        "authority": "Automotive Research Association of India (ARAI)",
        "official_source_url": "https://www.araiindia.com",
        "scope": "Pneumatic Tyres for Automotive Vehicles — Tread Wear Indicators (TWI)",
        "category": "Technical Manufacturing & Type-Approval Standard",
        "requirement": (
            "Mandatory molded Tread Wear Indicators (TWI) set at 0.8 mm for Category L and "
            "1.6 mm for Categories M & N across the tread breadth."
        ),
    },
    "oem_brake_guidelines": {
        "title": "Brake Lining Wear Limit (Manufacturer Service Guideline under CMVR Rule 96)",
        "legal_citation": "OEM Technical Service Specification; CMVR 1989 Rule 96 (Brakes)",
        "authority": "Automotive Manufacturer Engineering Practice (Not a Statutory Law Limit)",
        "official_source_url": "https://morth.nic.in/central-motor-vehicles-rules-1989",
        "scope": "Brake Lining & Disc Pad Friction Material Discard Limits",
        "category": "Advisory Engineering Practice & Manufacturer Service Guideline",
        "critical_discard_threshold_mm": 2.0,
        "advisory_replacement_threshold_mm": 3.5,
        "nominal_new_pad_thickness_mm": 10.0,
        "clarification": (
            "CMVR Rule 96 regulates stopping performance (braking efficiency percentages and stopping distance), "
            "not a universal millimeter lining thickness. AIS-061 regulates replacement lining type-approval. "
            "The 2.0 mm limit is an advisory industry engineering guideline to avoid backing plate rotor scoring."
        ),
    },
    "cmvr_rule_115": {
        "title": "Central Motor Vehicles Rules (CMVR) 1989 — Rule 115(7)",
        "legal_citation": "CMVR 1989, Rule 115, Sub-rule (7)",
        "authority": "Ministry of Road Transport and Highways (MoRTH), Government of India",
        "official_source_url": "https://morth.nic.in/emission-standards",
        "scope": "Mandatory In-Service Emission Certification (Pollution Under Control — PUC)",
        "category": "Statutory Indian Law",
        "legal_consequence": "Operating without a valid PUC is punishable under Section 190(2) of the Motor Vehicles Act, 1988.",
    },
    "mva_section_146": {
        "title": "Motor Vehicles Act, 1988 — Section 146",
        "legal_citation": "Motor Vehicles Act, 1988, Section 146",
        "authority": "Parliament of India / India Code",
        "official_source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "scope": "Mandatory Third-Party Insurance for Motor Vehicles",
        "category": "Statutory Indian Law",
        "legal_consequence": "Operating an uninsured motor vehicle is punishable under Section 196 of the Motor Vehicles Act, 1988.",
    },
    "cmvr_rule_52_62": {
        "title": "CMVR 1989 Rule 52 (Private Renewal) vs. Rule 62 (Transport Fitness)",
        "legal_citation": "MVA 1988 Sections 41 & 56; CMVR 1989 Rules 52 & 62",
        "authority": "Ministry of Road Transport and Highways (MoRTH), Government of India",
        "official_source_url": "https://morth.nic.in/central-motor-vehicles-rules-1989",
        "scope": "Registration Validity & Fitness Certification",
        "category": "Statutory Indian Law",
        "distinction": (
            "Private non-transport vehicles have 15-year initial registration under MVA Sec 41(7), "
            "renewable every 5 years under CMVR Rule 52. Transport (commercial) vehicles require periodic "
            "fitness certificates under MVA Sec 56 and CMVR Rule 62. Vehicle age alone does not constitute "
            "a violation if the registration renewal was completed."
        ),
    },
}

MANDATORY_DISCLAIMER_TEXT = (
    "ADVISORY NOTICE: This assessment is an automated preliminary engineering estimate derived "
    "from self-reported parameters and rule-based Indian automotive standards (CMVR 1989 "
    "and AIS). It DOES NOT certify that the vehicle is legally roadworthy, DOES NOT grant an RTO "
    "Certificate of Fitness or Registration Renewal, and DOES NOT guarantee mechanical or structural safety. "
    "All documentation statuses are user-provided and have NOT been validated against official government "
    "databases (e.g. VAHAN/Parivahan). A physical inspection at an authorized testing station (ATS) "
    "is indispensable before operating on public roadways."
)

LEGAL_DISCLAIMER_VERSION = "CMVR-AIS-Advisory-v2.0"


@dataclass
class ParameterAudit:
    """Detailed audit for a single vehicle parameter."""
    parameter: str
    measured_value: Any
    status: str  # 'compliant' | 'warning' | 'violation' | 'unverified'
    is_statutory: bool
    statutory_reference: str
    finding: str
    recommendation: str
    deduction_applied: float


@dataclass
class AssessmentOutput:
    """Structured assessment output."""
    preliminary_score: float
    risk_tier: str  # 'Low', 'Moderate', 'High', 'Critical'
    vehicle_category: str
    statutory_violations: List[str] = field(default_factory=list)
    advisory_warnings: List[str] = field(default_factory=list)
    critical_warnings: List[str] = field(default_factory=list)
    parameter_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    missing_unverified_attributes: List[str] = field(default_factory=list)
    data_completeness: str = "Standard"  # 'Comprehensive', 'Standard', 'Minimal'
    document_verification_source: str = "self_reported_unverified"
    disclaimer_text: str = MANDATORY_DISCLAIMER_TEXT
    legal_disclaimer_version: str = LEGAL_DISCLAIMER_VERSION


def evaluate_vehicle_safety(
    make: str,
    model: str,
    year: int,
    odometer_km: float,
    brake_pad_thickness_mm: Optional[float] = None,
    tyre_tread_depth_mm: Optional[float] = None,
    vehicle_category: Optional[str] = None,
    service_records_count: int = 0,
    past_accidents_count: int = 0,
    puc_valid: Optional[bool] = None,
    insurance_valid: Optional[bool] = None,
    fitness_certificate_valid: Optional[bool] = None,
    current_year: Optional[int] = None,
) -> AssessmentOutput:
    """Run deterministic, transparent rule-based vehicle safety assessment.

    Correctly applies category-specific Indian legal thresholds (CMVR 1989 Rule 95)
    and strictly separates statutory requirements from advisory maintenance guidelines.
    """
    now_year = current_year or datetime.now(timezone.utc).year
    vehicle_age = max(0, now_year - year)

    # Normalize vehicle category safely without accidental substring collision
    if not vehicle_category:
        resolved_category = VehicleCategory.UNKNOWN
    else:
        cat_str = vehicle_category.strip().lower()
        if (
            "commercial" in cat_str
            or "transport" in cat_str
            or "goods" in cat_str
            or "n1" in cat_str
            or "n2" in cat_str
            or "n3" in cat_str
        ):
            resolved_category = VehicleCategory.COMMERCIAL_TRANSPORT
        elif (
            cat_str.startswith("l_")
            or cat_str == "l"
            or "two_wheeler" in cat_str
            or "three_wheeler" in cat_str
            or "two-wheeler" in cat_str
            or "three-wheeler" in cat_str
            or "2w" in cat_str
            or "3w" in cat_str
            or "motorcycle" in cat_str
            or "scooter" in cat_str
            or "rickshaw" in cat_str
            or "quadricycle" in cat_str
        ):
            resolved_category = VehicleCategory.L_TWO_THREE_WHEELER
        elif "m1" in cat_str or "car" in cat_str or "passenger" in cat_str:
            resolved_category = VehicleCategory.M1_PASSENGER_CAR
        elif "unknown" in cat_str or "unverified" in cat_str:
            resolved_category = VehicleCategory.UNKNOWN
        else:
            resolved_category = VehicleCategory.UNKNOWN

    score = 100.0
    statutory_violations: List[str] = []
    advisory_warnings: List[str] = []
    critical_warnings: List[str] = []
    parameter_audits: List[ParameterAudit] = []
    missing_attributes: List[str] = []

    # ── 1. Tyre Tread Depth Evaluation (CMVR Rule 95(3)(iv) & AIS-044) ─────────
    if tyre_tread_depth_mm is None:
        missing_attributes.append("Tyre Non-Skid Tread Depth (Physical Measurement Missing)")
        parameter_audits.append(
            ParameterAudit(
                parameter="Tyre Tread Depth",
                measured_value="Missing / Not Provided",
                status="unverified",
                is_statutory=True,
                statutory_reference="CMVR 1989 Rule 95(3)(iv)",
                finding="Tyre tread depth measurement was not provided; legal compliance cannot be determined.",
                recommendation="Measure non-skid depth across primary tread grooves using a calibrated vernier or depth gauge.",
                deduction_applied=0.0,
            )
        )
    else:
        # Determine applicable statutory and advisory thresholds based on vehicle category
        if resolved_category == VehicleCategory.L_TWO_THREE_WHEELER:
            stat_limit = 0.8
            advisory_limit = 1.5
            cat_name = "Two/Three-Wheeler (Category L)"
        elif resolved_category == VehicleCategory.UNKNOWN:
            stat_limit = None
            advisory_limit = 2.0
            cat_name = "Unknown Category"
        else:
            # Default M1 / Commercial
            stat_limit = 1.6
            advisory_limit = 2.5
            cat_name = "Passenger Car / Motor Vehicle (Category M1)"

        if stat_limit is not None:
            # Exact boundary: tyre_tread_depth_mm < stat_limit is violation; >= stat_limit is compliant
            if tyre_tread_depth_mm < stat_limit:
                deduction = 45.0
                score -= deduction
                violation_msg = (
                    f"STATUTORY VIOLATION [CMVR Rule 95(3)(iv) & AIS-044]: Measured tread depth "
                    f"({tyre_tread_depth_mm:.2f} mm) is below the {stat_limit:.1f} mm legal limit for {cat_name}. "
                    f"Tyres are legally deemed not in good and sound condition under Motor Vehicles Act, 1988."
                )
                statutory_violations.append(violation_msg)
                critical_warnings.append(violation_msg)
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="violation",
                        is_statutory=True,
                        statutory_reference=f"CMVR 1989 Rule 95(3)(iv) [{cat_name}]",
                        finding=f"Tread depth ({tyre_tread_depth_mm:.2f} mm) violates the statutory minimum of {stat_limit:.1f} mm.",
                        recommendation="Immediate tyre replacement required before driving on public roads.",
                        deduction_applied=deduction,
                    )
                )
            elif tyre_tread_depth_mm < advisory_limit:
                deduction = 18.0
                score -= deduction
                warn_msg = (
                    f"ADVISORY WARNING [Tyre Industry Safety Buffer]: Tread depth ({tyre_tread_depth_mm:.2f} mm) "
                    f"meets the {stat_limit:.1f} mm statutory floor for {cat_name}, but is within the advisory wear window "
                    f"(< {advisory_limit:.1f} mm). Wet braking distances are significantly increased."
                )
                advisory_warnings.append(warn_msg)
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="warning",
                        is_statutory=False,
                        statutory_reference=f"AIS-044 / Tyre Engineering Buffer [{cat_name}]",
                        finding=f"Tread depth ({tyre_tread_depth_mm:.2f} mm) is legally compliant but in the advisory wear zone (< {advisory_limit:.1f} mm).",
                        recommendation="Plan tyre replacement within 3,000 km, especially prior to wet weather or highway driving.",
                        deduction_applied=deduction,
                    )
                )
            elif tyre_tread_depth_mm < 3.5:
                deduction = 6.0
                score -= deduction
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="compliant",
                        is_statutory=True,
                        statutory_reference=f"CMVR 1989 Rule 95(3)(iv) [{cat_name}]",
                        finding=f"Tread depth ({tyre_tread_depth_mm:.2f} mm) is legally compliant with moderate service wear.",
                        recommendation="Inspect tread wear every 5,000 km and maintain manufacturer cold inflation pressure.",
                        deduction_applied=deduction,
                    )
                )
            else:
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="compliant",
                        is_statutory=True,
                        statutory_reference=f"CMVR 1989 Rule 95(3)(iv) [{cat_name}]",
                        finding=f"Non-skid depth ({tyre_tread_depth_mm:.2f} mm) is well above statutory and advisory minimums.",
                        recommendation="Maintain standard tyre rotation intervals.",
                        deduction_applied=0.0,
                    )
                )
        else:
            # Category is UNKNOWN
            if tyre_tread_depth_mm < 0.8:
                # Below all vehicle category limits (even 2-wheelers)
                deduction = 45.0
                score -= deduction
                violation_msg = (
                    f"STATUTORY VIOLATION [CMVR Rule 95(3)(iv)]: Measured tread depth ({tyre_tread_depth_mm:.2f} mm) "
                    f"is below 0.8 mm, which is illegal for ALL vehicle categories in India."
                )
                statutory_violations.append(violation_msg)
                critical_warnings.append(violation_msg)
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="violation",
                        is_statutory=True,
                        statutory_reference="CMVR 1989 Rule 95(3)(iv)",
                        finding=f"Tread depth ({tyre_tread_depth_mm:.2f} mm) is below the minimum for all motor vehicle classes.",
                        recommendation="Immediate tyre replacement required.",
                        deduction_applied=deduction,
                    )
                )
            elif tyre_tread_depth_mm < 1.6:
                # Ambiguous: compliant for 2-wheelers (>=0.8 mm), violation for 4-wheelers (<1.6 mm)
                missing_attributes.append("Vehicle Category (Needed to determine whether 0.8 mm or 1.6 mm tyre rule applies)")
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="unverified",
                        is_statutory=True,
                        statutory_reference="CMVR 1989 Rule 95(3)(iv)",
                        finding=(
                            f"Tread depth is {tyre_tread_depth_mm:.2f} mm. This is compliant for Category L (2/3-wheelers, min 0.8 mm) "
                            f"but a violation for Category M1 (passenger cars, min 1.6 mm). Category must be specified."
                        ),
                        recommendation="Specify vehicle category to evaluate statutory compliance accurately.",
                        deduction_applied=0.0,
                    )
                )
            else:
                parameter_audits.append(
                    ParameterAudit(
                        parameter="Tyre Tread Depth",
                        measured_value=f"{tyre_tread_depth_mm:.2f} mm",
                        status="compliant",
                        is_statutory=True,
                        statutory_reference="CMVR 1989 Rule 95(3)(iv)",
                        finding=f"Tread depth ({tyre_tread_depth_mm:.2f} mm) is compliant for all vehicle categories (>= 1.6 mm).",
                        recommendation="Maintain standard rotation intervals.",
                        deduction_applied=0.0,
                    )
                )

    # ── 2. Brake Pad Thickness Evaluation (Advisory OEM Practice / CMVR Rule 96) ─
    # Clarification: 2.0 mm is an advisory manufacturer discard threshold, NOT a statutory law limit.
    if brake_pad_thickness_mm is None:
        missing_attributes.append("Brake Pad Lining Thickness (Physical Measurement Missing)")
        parameter_audits.append(
            ParameterAudit(
                parameter="Brake Pad Thickness",
                measured_value="Missing / Not Provided",
                status="unverified",
                is_statutory=False,
                statutory_reference="Manufacturer Service Specification",
                finding="Brake pad thickness measurement not provided; friction wear cannot be evaluated.",
                recommendation="Physically inspect disc brake pads with a lining thickness gauge during wheel-off service.",
                deduction_applied=0.0,
            )
        )
    else:
        # Boundary: < 2.0 mm is critical wear; 2.0 mm <= pad < 3.5 mm is advisory wear
        if brake_pad_thickness_mm < 2.0:
            deduction = 40.0
            score -= deduction
            crit_msg = (
                f"CRITICAL MECHANICAL RISK [Manufacturer Discard Guideline]: Measured brake pad thickness "
                f"({brake_pad_thickness_mm:.2f} mm) is below the 2.0 mm industry discard limit. "
                f"Severe hazard of steel backing plate gouging brake discs, brake fluid overheating, and extended stopping distance."
            )
            critical_warnings.append(crit_msg)
            # Important: It is a critical mechanical advisory, NOT a statutory violation under law.
            parameter_audits.append(
                ParameterAudit(
                    parameter="Brake Pad Thickness",
                    measured_value=f"{brake_pad_thickness_mm:.2f} mm",
                    status="warning",
                    is_statutory=False,
                    statutory_reference="Manufacturer Service Guideline (Braking Safety under CMVR Rule 96)",
                    finding=f"Friction lining ({brake_pad_thickness_mm:.2f} mm) has breached the 2.0 mm manufacturer discard threshold.",
                    recommendation="Do not operate at highway speeds. Replace front and rear brake pads immediately.",
                    deduction_applied=deduction,
                )
            )
        elif brake_pad_thickness_mm < 3.5:
            deduction = 15.0
            score -= deduction
            warn_msg = (
                f"ADVISORY WARNING [Maintenance Alert]: Brake pad thickness ({brake_pad_thickness_mm:.2f} mm) "
                f"is in the advisory replacement window (2.0–3.5 mm). Friction material is nearing end of operational life."
            )
            advisory_warnings.append(warn_msg)
            parameter_audits.append(
                ParameterAudit(
                    parameter="Brake Pad Thickness",
                    measured_value=f"{brake_pad_thickness_mm:.2f} mm",
                    status="warning",
                    is_statutory=False,
                    statutory_reference="Manufacturer Service Specification",
                    finding=f"Pad thickness ({brake_pad_thickness_mm:.2f} mm) is in the advisory replacement range (2.0–3.5 mm).",
                    recommendation="Schedule brake pad replacement during next scheduled service or within 2,500 km.",
                    deduction_applied=deduction,
                )
            )
        elif brake_pad_thickness_mm < 5.0:
            deduction = 5.0
            score -= deduction
            parameter_audits.append(
                ParameterAudit(
                    parameter="Brake Pad Thickness",
                    measured_value=f"{brake_pad_thickness_mm:.2f} mm",
                    status="compliant",
                    is_statutory=False,
                    statutory_reference="Manufacturer Service Specification",
                    finding=f"Brake pad thickness ({brake_pad_thickness_mm:.2f} mm) provides adequate stopping margins.",
                    recommendation="Inspect brake calipers and rotor runout at regular service intervals.",
                    deduction_applied=deduction,
                )
            )
        else:
            parameter_audits.append(
                ParameterAudit(
                    parameter="Brake Pad Thickness",
                    measured_value=f"{brake_pad_thickness_mm:.2f} mm",
                    status="compliant",
                    is_statutory=False,
                    statutory_reference="Manufacturer Service Specification",
                    finding=f"Substantial friction material remaining ({brake_pad_thickness_mm:.2f} mm).",
                    recommendation="Brake friction components are in satisfactory condition.",
                    deduction_applied=0.0,
                )
            )

    # ── 3. Usage & Duty Cycle Analysis ──────────────────────────────────────
    annual_km = odometer_km / max(1.0, float(vehicle_age))
    if vehicle_age > 0 and annual_km > 28000.0:
        deduction = 8.0
        score -= deduction
        warn_msg = (
            f"LIFECYCLE ADVISORY: High annual usage ({annual_km:,.0f} km/year). "
            f"Indicates intense commercial fleet or long-distance highway duty cycle."
        )
        advisory_warnings.append(warn_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="Usage & Duty Cycle",
                measured_value=f"{annual_km:,.0f} km/yr",
                status="warning",
                is_statutory=False,
                statutory_reference="Automotive Duty Cycle Heuristics",
                finding=f"Annual usage of {annual_km:,.0f} km/yr exceeds private vehicle average (10,000–15,000 km/yr).",
                recommendation="Inspect suspension ball joints, tie rod ends, and engine mounts for accelerated wear.",
                deduction_applied=deduction,
            )
        )
    elif vehicle_age >= 7 and annual_km < 2500.0 and odometer_km > 5000:
        deduction = 5.0
        score -= deduction
        warn_msg = (
            f"LIFECYCLE ADVISORY: Exceptionally low annual usage ({annual_km:,.0f} km/year) for a {vehicle_age}-year-old vehicle. "
            f"Potential stagnation degradation (rubber hardening, moisture in fluid systems). Verify odometer against service logs."
        )
        advisory_warnings.append(warn_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="Usage & Duty Cycle",
                measured_value=f"{annual_km:,.0f} km/yr",
                status="warning",
                is_statutory=False,
                statutory_reference="Automotive Maintenance & Stagnation Heuristics",
                finding=f"Low usage ({annual_km:,.0f} km/yr) over {vehicle_age} years. Risk of stagnation degradation.",
                recommendation="Verify odometer continuity in authorized workshop service records.",
                deduction_applied=deduction,
            )
        )
    else:
        parameter_audits.append(
            ParameterAudit(
                parameter="Usage & Duty Cycle",
                measured_value=f"{annual_km:,.0f} km/yr",
                status="compliant",
                is_statutory=False,
                statutory_reference="Automotive Industry Average",
                finding=f"Annual usage of {annual_km:,.0f} km/yr aligns with typical duty cycles.",
                recommendation="Continue adhering to standard manufacturer maintenance schedule.",
                deduction_applied=0.0,
            )
        )

    # ── 4. Accident History & Structural Integrity ──────────────────────────
    if past_accidents_count > 0:
        deduction = min(25.0, past_accidents_count * 10.0)
        score -= deduction
        warn_msg = (
            f"STRUCTURAL INTEGRITY ADVISORY: Vehicle has {past_accidents_count} reported accident history record(s). "
            f"Risk of structural chassis misalignment, compromised crumple zones, or non-deployed/repaired airbag modules."
        )
        critical_warnings.append(warn_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="Accident History",
                measured_value=f"{past_accidents_count} incident(s)",
                status="warning" if past_accidents_count == 1 else "violation",
                is_statutory=False,
                statutory_reference="Structural Collision Repair Standards (AIS-029/AIS-096)",
                finding=f"Recorded past accident history ({past_accidents_count} incidents).",
                recommendation="Perform 3D laser chassis alignment inspection and diagnostic airbag module scan.",
                deduction_applied=deduction,
            )
        )
    else:
        parameter_audits.append(
            ParameterAudit(
                parameter="Accident History",
                measured_value="0 reported incidents",
                status="compliant",
                is_statutory=False,
                statutory_reference="Self-Reported Collision Record",
                finding="No prior collision or structural repair records reported by user.",
                recommendation="Confirm chassis aprons and pillar spot welds show original factory sealant.",
                deduction_applied=0.0,
            )
        )

    # ── 5. Service Records Maintenance Trail ────────────────────────────────
    if service_records_count == 0 and odometer_km > 25000:
        deduction = 8.0
        score -= deduction
        warn_msg = (
            f"MAINTENANCE DOCUMENTATION: Zero documented service records provided for a vehicle "
            f"with {odometer_km:,.0f} km. Inability to verify timing belt, coolant, and brake fluid maintenance history."
        )
        advisory_warnings.append(warn_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="Service Documentation",
                measured_value="0 records",
                status="warning",
                is_statutory=False,
                statutory_reference="Preventative Maintenance Best Practices",
                finding=f"Lack of service records for vehicle with {odometer_km:,.0f} km.",
                recommendation="Perform comprehensive fluid flush (brake fluid, coolant, transmission) and belt inspection.",
                deduction_applied=deduction,
            )
        )
    else:
        parameter_audits.append(
            ParameterAudit(
                parameter="Service Documentation",
                measured_value=f"{service_records_count} records",
                status="compliant",
                is_statutory=False,
                statutory_reference="Preventative Maintenance Best Practices",
                finding=f"{service_records_count} documented maintenance record(s) provided.",
                recommendation="Continue preserving authorized workshop job cards and invoices.",
                deduction_applied=0.0,
            )
        )

    # ── 6. Statutory Documentation Verification (PUC, Fitness, Insurance) ─────
    # PUC (CMVR Rule 115(7))
    if puc_valid is True:
        parameter_audits.append(
            ParameterAudit(
                parameter="PUC Certificate",
                measured_value="Reported Valid (Self-Reported)",
                status="compliant",
                is_statutory=True,
                statutory_reference="CMVR 1989 Rule 115(7)",
                finding="Pollution Under Control (PUC) certificate reported valid by user. Note: Not verified against Parivahan database.",
                recommendation="Ensure periodic renewal within specified 6-month / 1-year statutory validity window.",
                deduction_applied=0.0,
            )
        )
    elif puc_valid is False:
        deduction = 5.0
        score -= deduction
        stat_msg = (
            "STATUTORY VIOLATION [CMVR Rule 115(7)]: Pollution Under Control (PUC) certificate is expired or invalid. "
            "Operating without a valid PUC certificate is punishable under Section 190(2) of the Motor Vehicles Act, 1988."
        )
        statutory_violations.append(stat_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="PUC Certificate",
                measured_value="Expired / Invalid (Self-Reported)",
                status="violation",
                is_statutory=True,
                statutory_reference="CMVR 1989 Rule 115(7) & MVA Sec 190(2)",
                finding="Vehicle reported to lack valid emission compliance certification.",
                recommendation="Conduct mandatory emission testing at an authorized RTO testing centre immediately.",
                deduction_applied=deduction,
            )
        )
    else:
        missing_attributes.append("PUC Certificate Status (Not Provided / Unverified)")
        parameter_audits.append(
            ParameterAudit(
                parameter="PUC Certificate",
                measured_value="Unverified / Not Provided",
                status="unverified",
                is_statutory=True,
                statutory_reference="CMVR 1989 Rule 115(7)",
                finding="PUC validity status not provided; compliance cannot be confirmed without checking VAHAN / emission logs.",
                recommendation="Verify active PUC certificate validity via Parivahan portal.",
                deduction_applied=0.0,
            )
        )

    # Third-Party Motor Insurance (MVA 1988 Section 146)
    if insurance_valid is True:
        parameter_audits.append(
            ParameterAudit(
                parameter="Motor Insurance",
                measured_value="Reported Active (Self-Reported)",
                status="compliant",
                is_statutory=True,
                statutory_reference="Motor Vehicles Act, 1988 (Section 146)",
                finding="Third-party liability motor insurance reported active by user. Note: Not verified against IIB / insurer API.",
                recommendation="Maintain continuous insurance policy coverage without lapsing.",
                deduction_applied=0.0,
            )
        )
    elif insurance_valid is False:
        deduction = 5.0
        score -= deduction
        stat_msg = (
            "STATUTORY VIOLATION [MVA Section 146]: Mandatory Third-Party Insurance is expired or absent. "
            "Vehicle cannot legally ply on any public road in India under Section 196 of the Motor Vehicles Act, 1988."
        )
        statutory_violations.append(stat_msg)
        parameter_audits.append(
            ParameterAudit(
                parameter="Motor Insurance",
                measured_value="Expired / Uninsured (Self-Reported)",
                status="violation",
                is_statutory=True,
                statutory_reference="Motor Vehicles Act, 1988 (Section 146)",
                finding="Mandatory motor insurance policy is reported inactive or expired.",
                recommendation="Renew minimum Third-Party liability insurance before operating vehicle on public roads.",
                deduction_applied=deduction,
            )
        )
    else:
        missing_attributes.append("Motor Insurance Policy Status (Not Provided / Unverified)")
        parameter_audits.append(
            ParameterAudit(
                parameter="Motor Insurance",
                measured_value="Unverified / Not Provided",
                status="unverified",
                is_statutory=True,
                statutory_reference="Motor Vehicles Act, 1988 (Section 146)",
                finding="Insurance policy status not provided; compliance cannot be confirmed without policy documentation.",
                recommendation="Check active insurance coverage via Parivahan or insurer policy records.",
                deduction_applied=0.0,
            )
        )

    # Vehicle Age & Registration / Fitness Renewal
    # Strict separation: Non-transport (private) 15-year renewal vs Transport (commercial) fitness vs Unknown
    if resolved_category == VehicleCategory.COMMERCIAL_TRANSPORT:
        # Commercial transport: Periodic Fitness Certificate under MVA Sec 56 & CMVR Rule 62
        if fitness_certificate_valid is True:
            parameter_audits.append(
                ParameterAudit(
                    parameter="Commercial Fitness Certificate",
                    measured_value="Reported Valid (Self-Reported)",
                    status="compliant",
                    is_statutory=True,
                    statutory_reference="CMVR 1989 Rule 62 & MVA Sec 56",
                    finding="Commercial transport vehicle reported to hold valid fitness certificate.",
                    recommendation="Ensure periodic physical inspection at an authorized testing station (ATS).",
                    deduction_applied=0.0,
                )
            )
        elif fitness_certificate_valid is False:
            deduction = 15.0
            score -= deduction
            stat_msg = (
                "STATUTORY VIOLATION [CMVR Rule 62 & MVA Sec 56]: Commercial transport vehicle fitness certificate "
                "is expired or invalid. Under Section 56 of the Motor Vehicles Act, 1988, a transport vehicle without "
                "a valid fitness certificate is deemed not validly registered."
            )
            statutory_violations.append(stat_msg)
            critical_warnings.append(stat_msg)
            parameter_audits.append(
                ParameterAudit(
                    parameter="Commercial Fitness Certificate",
                    measured_value="Expired / Invalid (Self-Reported)",
                    status="violation",
                    is_statutory=True,
                    statutory_reference="CMVR 1989 Rule 62 & MVA Sec 56",
                    finding="Commercial vehicle lacks valid fitness certification required for transport operation.",
                    recommendation="Submit vehicle immediately for fitness test at an authorized testing station.",
                    deduction_applied=deduction,
                )
            )
        else:
            missing_attributes.append("Commercial Fitness Certificate (CMVR Rule 62 / MVA Sec 56)")
            parameter_audits.append(
                ParameterAudit(
                    parameter="Commercial Fitness Certificate",
                    measured_value="Unverified / Not Provided",
                    status="unverified",
                    is_statutory=True,
                    statutory_reference="CMVR 1989 Rule 62 & MVA Sec 56",
                    finding="Fitness certificate status not provided for commercial transport vehicle.",
                    recommendation="Obtain and verify valid Form 38 fitness certificate.",
                    deduction_applied=0.0,
                )
            )
    elif resolved_category in (VehicleCategory.M1_PASSENGER_CAR, VehicleCategory.L_TWO_THREE_WHEELER):
        # Non-transport / Private Vehicle: 15-Year Registration Renewal under MVA Sec 41(8) & CMVR Rule 52
        if vehicle_age < 15:
            parameter_audits.append(
                ParameterAudit(
                    parameter="15-Year Registration Validity",
                    measured_value=f"Vehicle age: {vehicle_age} yrs (Initial 15-Yr Window Active)",
                    status="compliant",
                    is_statutory=True,
                    statutory_reference="MVA 1988 Section 41(7)",
                    finding=f"Vehicle age ({vehicle_age} yrs) is within the initial 15-year statutory registration validity window.",
                    recommendation="Registration renewal will be required upon vehicle reaching 15 years from date of registration.",
                    deduction_applied=0.0,
                )
            )
        else:
            # Vehicle age >= 15 years
            if fitness_certificate_valid is True:
                parameter_audits.append(
                    ParameterAudit(
                        parameter="15-Year Registration Renewal",
                        measured_value=f"Vehicle age: {vehicle_age} yrs (Reported Renewed)",
                        status="compliant",
                        is_statutory=True,
                        statutory_reference="MVA 1988 Sec 41(8) & CMVR Rule 52",
                        finding="Registration renewal for vehicle > 15 years reported valid by user.",
                        recommendation="Maintain valid 5-year renewal certificate issued by registering authority.",
                        deduction_applied=0.0,
                    )
                )
            elif fitness_certificate_valid is False:
                deduction = 15.0
                score -= deduction
                stat_msg = (
                    f"STATUTORY VIOLATION [MVA Sec 41(8) & CMVR Rule 52]: Vehicle age is {vehicle_age} years "
                    f"(>= 15 years) and registration renewal is reported expired or not completed. "
                    f"Under Section 41(7) of the Motor Vehicles Act, 1988, private vehicle registration lapses after 15 years unless renewed."
                )
                statutory_violations.append(stat_msg)
                critical_warnings.append(stat_msg)
                parameter_audits.append(
                    ParameterAudit(
                        parameter="15-Year Registration Renewal",
                        measured_value=f"Vehicle age: {vehicle_age} yrs (Unrenewed)",
                        status="violation",
                        is_statutory=True,
                        statutory_reference="MVA 1988 Sec 41(8) & CMVR Rule 52",
                        finding="Vehicle exceeds 15-year statutory age threshold without verified registration renewal.",
                        recommendation="Submit vehicle for physical inspection and registration renewal (Form 25) at the jurisdictional RTO / ATS.",
                        deduction_applied=deduction,
                    )
                )
            else:
                missing_attributes.append(f"15-Year Registration Renewal Certificate (Vehicle Age: {vehicle_age} yrs)")
                parameter_audits.append(
                    ParameterAudit(
                        parameter="15-Year Registration Renewal",
                        measured_value=f"Vehicle age: {vehicle_age} yrs (Status Unverified)",
                        status="unverified",
                        is_statutory=True,
                        statutory_reference="MVA 1988 Sec 41(8) & CMVR Rule 52",
                        finding=(
                            f"Vehicle is {vehicle_age} years old (>= 15 years). Registration renewal status was not provided. "
                            f"Age alone does not establish a violation without checking RTO records."
                        ),
                        recommendation="Verify whether Form 25 registration renewal was completed via VAHAN.",
                        deduction_applied=0.0,
                    )
                )
    else:
        # Category is UNKNOWN: Cannot determine whether Rule 52 (private) or Rule 62 (commercial) applies
        if fitness_certificate_valid is True:
            parameter_audits.append(
                ParameterAudit(
                    parameter="Registration / Fitness Certification",
                    measured_value="Reported Valid (Self-Reported)",
                    status="compliant",
                    is_statutory=True,
                    statutory_reference="MVA 1988 Sec 41 / Sec 56",
                    finding="Registration or fitness validity reported active by user.",
                    recommendation="Ensure category-specific certificates (Form 25 or Form 38) remain active.",
                    deduction_applied=0.0,
                )
            )
        elif fitness_certificate_valid is False:
            deduction = 15.0
            score -= deduction
            stat_msg = (
                "STATUTORY VIOLATION [MVA 1988 Sec 41/56]: Vehicle registration or fitness certificate is reported invalid or expired."
            )
            statutory_violations.append(stat_msg)
            critical_warnings.append(stat_msg)
            parameter_audits.append(
                ParameterAudit(
                    parameter="Registration / Fitness Certification",
                    measured_value="Expired / Invalid (Self-Reported)",
                    status="violation",
                    is_statutory=True,
                    statutory_reference="MVA 1988 Sec 41 / Sec 56",
                    finding="Vehicle reported to lack valid registration or mandatory fitness certification.",
                    recommendation="Obtain valid registration renewal or fitness certificate at an authorized testing station.",
                    deduction_applied=deduction,
                )
            )
        else:
            missing_attributes.append("Registration / Fitness Certificate (Vehicle Category Unknown)")
            parameter_audits.append(
                ParameterAudit(
                    parameter="Registration / Fitness Certification",
                    measured_value="Unverified / Category Unknown",
                    status="unverified",
                    is_statutory=True,
                    statutory_reference="MVA 1988 Sec 41 & 56",
                    finding="Vehicle category is unknown; cannot determine whether 15-year private renewal (Rule 52) or commercial transport fitness (Rule 62) applies.",
                    recommendation="Specify vehicle category to determine whether CMVR Rule 52 or Rule 62 applies.",
                    deduction_applied=0.0,
                )
            )

    # ── Missing Structural / Technical Areas (Identified for Transparency) ───
    missing_attributes.extend([
        "Physical Chassis & Frame Alignment (Laser Calibration)",
        "OBD-II Diagnostic Trouble Codes (DTCs / Airbag / ABS Sensors)",
        "Brake Fluid Boiling Point & Moisture Saturation",
        "Suspension Damping Rate & Ball Joint Radial Play",
        "Headlamp Beam Alignment & Photometric Intensity (CMVR Rule 105)",
    ])

    # ── Enforce Hard Risk-Tier Caps & Score Bounds ────────────────────────────
    # Hard rule: If statutory violations exist, score cannot exceed 35.0
    if statutory_violations:
        score = min(score, 35.0)

    # Hard rule: If critical brake wear (< 2.0 mm) exists, score cannot exceed 35.0
    if brake_pad_thickness_mm is not None and brake_pad_thickness_mm < 2.0:
        score = min(score, 35.0)

    score = max(0.0, min(100.0, round(score, 1)))

    # Data completeness categorization
    provided_evidence_count = sum([
        tyre_tread_depth_mm is not None,
        brake_pad_thickness_mm is not None,
        puc_valid is not None,
        insurance_valid is not None,
    ])
    if provided_evidence_count == 4:
        data_completeness = "Comprehensive"
    elif provided_evidence_count >= 2:
        data_completeness = "Standard"
    else:
        data_completeness = "Minimal"

    # ── Explicit Priority Order for Risk Tier Determination ───────────────────
    # Priority 1: Confirmed Critical Safety Finding or Statutory Violation
    # Incomplete or missing evidence NEVER downgrades a confirmed critical finding or violation!
    if len(statutory_violations) > 0 or len(critical_warnings) > 0 or score < 40.0:
        risk_tier = "Critical"

    # Priority 2: Confirmed Substantial Mechanical/Operational Degradation
    elif score < 60.0:
        risk_tier = "High"

    # Priority 3: Confirmed Advisory Concerns / Moderate Wear
    elif score < 80.0:
        risk_tier = "Moderate"

    # Priority 4 & 5: Score >= 80.0 (No confirmed critical/high/moderate defects)
    else:
        # Check if essential safety measurements are missing/unverified
        essential_measurements_missing = (tyre_tread_depth_mm is None or brake_pad_thickness_mm is None)
        category_unverified = (resolved_category == VehicleCategory.UNKNOWN)
        data_insufficient = (provided_evidence_count < 2)

        if essential_measurements_missing or category_unverified or data_insufficient:
            # Essential measurements unavailable: cannot assign "Low Risk".
            # Missing evidence is not a confirmed defect, so it is capped at "Moderate" (cautionary).
            risk_tier = "Moderate"

            if tyre_tread_depth_mm is None and brake_pad_thickness_mm is None:
                advisory_warnings.append(
                    "UNVERIFIED RUNNING GEAR ADVISORY: Both tyre tread depth and brake pad thickness are missing. "
                    "Assessment is capped at Moderate (Cautionary) because physical running gear is unverified."
                )
            elif tyre_tread_depth_mm is None:
                advisory_warnings.append(
                    "UNVERIFIED TYRE ADVISORY: Tyre tread depth was not provided. "
                    "Assessment is capped at Moderate pending non-skid depth verification."
                )
            elif brake_pad_thickness_mm is None:
                advisory_warnings.append(
                    "UNVERIFIED BRAKE ADVISORY: Brake pad thickness was not provided. "
                    "Assessment is capped at Moderate pending friction lining inspection."
                )

            if category_unverified:
                advisory_warnings.append(
                    "CATEGORY ADVISORY: Vehicle category is unknown. "
                    "Assessment is capped at Moderate because category-specific rules cannot be confirmed."
                )
        else:
            # Complete verified compliant evidence with score >= 80.0
            risk_tier = "Low"

    return AssessmentOutput(
        preliminary_score=score,
        risk_tier=risk_tier,
        vehicle_category=resolved_category.value,
        statutory_violations=statutory_violations,
        advisory_warnings=advisory_warnings,
        critical_warnings=critical_warnings,
        parameter_breakdown=[
            {
                "parameter": a.parameter,
                "measured_value": a.measured_value,
                "status": a.status,
                "is_statutory": a.is_statutory,
                "statutory_reference": a.statutory_reference,
                "finding": a.finding,
                "recommendation": a.recommendation,
                "deduction_applied": a.deduction_applied,
            }
            for a in parameter_audits
        ],
        missing_unverified_attributes=missing_attributes,
        data_completeness=data_completeness,
        document_verification_source="self_reported_unverified",
        disclaimer_text=MANDATORY_DISCLAIMER_TEXT,
        legal_disclaimer_version=LEGAL_DISCLAIMER_VERSION,
    )
