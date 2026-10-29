"""Comprehensive Test Suite for Phase 4 Vehicle Safety Assessment Module & Endpoints.

Validates:
  1. Category-specific tyre tread thresholds under CMVR Rule 95(3)(iv) (M1: 1.6 mm, L: 0.8 mm).
  2. Boundary conditions immediately below, at, and above statutory limits (1.59 vs 1.60 vs 1.61 mm; 0.79 vs 0.80 vs 0.81 mm).
  3. Missing / unknown vehicle category handling (unverified status).
  4. Advisory brake lining classification (never a false statutory violation).
  5. Missing tyre and brake evidence handled transparently as UNVERIFIED.
  6. Private vs. transport vehicle age/fitness distinction (CMVR Rule 52 vs Rule 62).
  7. Missing vs. expired document evidence (PUC, Insurance, Registration).
  8. User-reported evidence transparency (document_verification_source).
  9. Disclaimer enforcement and API boundary validation.
  10. Risk score and severity consistency.
  11. Persistence and retrieval via API.
"""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.vehicle_rules import (
    evaluate_vehicle_safety,
    VehicleCategory,
    STANDARDS_REGISTRY,
    MANDATORY_DISCLAIMER_TEXT,
)
from app.core.database import get_db


# ── Step 1: Category-Specific Tyre & Boundary Value Tests ───────────────────

def test_m1_passenger_car_tyre_statutory_violation():
    """Verify passenger car with tyre < 1.6 mm triggers a statutory violation under CMVR Rule 95."""
    result = evaluate_vehicle_safety(
        make="Maruti Suzuki",
        model="Swift",
        year=2018,
        odometer_km=50000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=1.59,  # Boundary test: immediately below 1.60 mm limit
        service_records_count=5,
    )
    assert result.risk_tier == "Critical"
    assert result.preliminary_score <= 35.0
    assert len(result.statutory_violations) == 1
    assert "CMVR Rule 95(3)(iv)" in result.statutory_violations[0]
    assert "1.6 mm" in result.statutory_violations[0]

    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "violation"
    assert tyre_audit["is_statutory"] is True


def test_m1_passenger_car_tyre_boundary_at_limit():
    """Verify passenger car with tyre exactly at 1.60 mm is legally compliant."""
    result = evaluate_vehicle_safety(
        make="Maruti Suzuki",
        model="Swift",
        year=2020,
        odometer_km=30000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=1.60,  # Boundary test: exactly at 1.60 mm statutory limit
        service_records_count=4,
    )
    # Must NOT be a statutory violation
    assert len(result.statutory_violations) == 0
    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "warning"  # In advisory wear buffer (1.6 to 2.5 mm)
    assert tyre_audit["is_statutory"] is False


def test_m1_passenger_car_tyre_boundary_above_limit():
    """Verify passenger car with tyre at 1.61 mm is compliant (advisory buffer)."""
    result = evaluate_vehicle_safety(
        make="Hyundai",
        model="i20",
        year=2021,
        odometer_km=25000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=1.61,  # Boundary test: immediately above 1.60 mm
        service_records_count=3,
    )
    assert len(result.statutory_violations) == 0
    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "warning"
    assert tyre_audit["is_statutory"] is False


def test_l_two_wheeler_tyre_category_specific_threshold():
    """Verify 2-wheeler with 1.2 mm tyre is legally compliant (limit is 0.8 mm, not 1.6 mm)."""
    result = evaluate_vehicle_safety(
        make="Hero",
        model="Splendor",
        year=2021,
        odometer_km=15000.0,
        vehicle_category="L_two_three_wheeler",
        brake_pad_thickness_mm=4.0,
        tyre_tread_depth_mm=1.2,  # Compliant for 2W (>=0.8 mm), but would violate 1.6 mm car rule!
        service_records_count=2,
    )
    assert len(result.statutory_violations) == 0
    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "warning"  # In advisory buffer (< 1.5 mm for 2W)
    assert tyre_audit["is_statutory"] is False


def test_l_two_wheeler_tyre_boundary_below_and_at_limit():
    """Verify boundary tests for 2-wheeler at 0.79 mm (violation) and 0.80 mm (compliant)."""
    # 0.79 mm -> statutory violation
    res_viol = evaluate_vehicle_safety(
        make="Bajaj",
        model="Pulsar",
        year=2019,
        odometer_km=30000.0,
        vehicle_category="L_two_three_wheeler",
        tyre_tread_depth_mm=0.79,
    )
    assert len(res_viol.statutory_violations) == 1
    assert "0.8 mm" in res_viol.statutory_violations[0]

    # 0.80 mm -> compliant (advisory buffer)
    res_comp = evaluate_vehicle_safety(
        make="Bajaj",
        model="Pulsar",
        year=2019,
        odometer_km=30000.0,
        vehicle_category="L_two_three_wheeler",
        tyre_tread_depth_mm=0.80,
    )
    assert len(res_comp.statutory_violations) == 0


def test_unknown_vehicle_category_ambiguity_handling():
    """Verify unknown category with 1.2 mm tread is flagged as UNVERIFIED rather than guessing."""
    result = evaluate_vehicle_safety(
        make="Generic",
        model="Vehicle",
        year=2020,
        odometer_km=20000.0,
        vehicle_category="unknown",
        tyre_tread_depth_mm=1.2,  # Between 0.8 mm (2W) and 1.6 mm (car)
    )
    assert len(result.statutory_violations) == 0
    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "unverified"
    assert "Category must be specified" in tyre_audit["finding"]


# ── Step 2: Brake Lining Threshold & Advisory Classification ────────────────

def test_brake_pad_critical_wear_is_advisory_not_statutory():
    """Verify brake pad < 2.0 mm triggers critical mechanical warning, NOT a false statutory violation."""
    result = evaluate_vehicle_safety(
        make="Tata",
        model="Nexon",
        year=2020,
        odometer_km=45000.0,
        brake_pad_thickness_mm=1.4,  # Below 2.0 mm manufacturer discard limit
        tyre_tread_depth_mm=4.0,     # healthy
    )
    # Must NOT produce a statutory violation
    assert len(result.statutory_violations) == 0

    # Must produce a critical mechanical risk warning
    assert len(result.critical_warnings) >= 1
    assert "Manufacturer Discard Guideline" in result.critical_warnings[0]

    # Score must be capped due to critical mechanical hazard
    assert result.preliminary_score <= 35.0
    assert result.risk_tier == "Critical"

    brake_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Brake Pad Thickness")
    assert brake_audit["is_statutory"] is False
    assert brake_audit["status"] == "warning"


def test_brake_pad_boundary_at_and_above_discard_limit():
    """Verify brake pad boundary at 2.00 mm (advisory window) and 3.50 mm (adequate)."""
    # Exactly 2.00 mm -> advisory replacement window
    res_2mm = evaluate_vehicle_safety(
        make="Honda",
        model="City",
        year=2020,
        odometer_km=35000.0,
        brake_pad_thickness_mm=2.00,
        tyre_tread_depth_mm=4.0,
    )
    assert len(res_2mm.critical_warnings) == 0
    assert len(res_2mm.advisory_warnings) >= 1
    assert any("Brake pad thickness" in w for w in res_2mm.advisory_warnings)

    # 5.00 mm -> compliant
    res_5mm = evaluate_vehicle_safety(
        make="Honda",
        model="City",
        year=2020,
        odometer_km=35000.0,
        brake_pad_thickness_mm=5.00,
        tyre_tread_depth_mm=4.0,
    )
    brake_audit = next(p for p in res_5mm.parameter_breakdown if p["parameter"] == "Brake Pad Thickness")
    assert brake_audit["status"] == "compliant"
    assert brake_audit["deduction_applied"] == 0.0


# ── Step 3: Missing Evidence & Unverified Attributes ────────────────────────

def test_missing_tyre_and_brake_evidence_handled_as_unverified():
    """Verify missing tyre and brake measurements are flagged as UNVERIFIED with zero penalty."""
    result = evaluate_vehicle_safety(
        make="Toyota",
        model="Corolla",
        year=2020,
        odometer_km=30000.0,
        brake_pad_thickness_mm=None,  # Missing
        tyre_tread_depth_mm=None,     # Missing
    )
    assert len(result.statutory_violations) == 0
    assert len(result.critical_warnings) == 0

    tyre_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit["status"] == "unverified"
    assert tyre_audit["deduction_applied"] == 0.0

    brake_audit = next(p for p in result.parameter_breakdown if p["parameter"] == "Brake Pad Thickness")
    assert brake_audit["status"] == "unverified"
    assert brake_audit["deduction_applied"] == 0.0


# ── Step 4: Private vs Commercial Vehicle Age & Fitness ──────────────────────

def test_private_vehicle_under_15_years_registration_valid():
    """Verify private vehicle under 15 years is compliant under MVA Section 41(7)."""
    result = evaluate_vehicle_safety(
        make="Hyundai",
        model="Creta",
        year=2018,
        current_year=2024,  # Age = 6 years (< 15)
        odometer_km=40000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=6.0,
        tyre_tread_depth_mm=4.0,
    )
    assert len(result.statutory_violations) == 0
    reg_audit = next(p for p in result.parameter_breakdown if "Registration" in p["parameter"])
    assert reg_audit["status"] == "compliant"
    assert "MVA 1988 Section 41(7)" in reg_audit["statutory_reference"]


def test_private_vehicle_over_15_years_renewed():
    """Verify private vehicle >= 15 years with renewed registration is compliant under CMVR Rule 52."""
    result = evaluate_vehicle_safety(
        make="Maruti",
        model="Zen",
        year=2005,
        current_year=2024,  # Age = 19 years (>= 15)
        odometer_km=110000.0,
        vehicle_category="M1_passenger_car",
        fitness_certificate_valid=True,  # Renewed registration
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=3.5,
    )
    assert len(result.statutory_violations) == 0
    reg_audit = next(p for p in result.parameter_breakdown if "Registration" in p["parameter"])
    assert reg_audit["status"] == "compliant"


def test_private_vehicle_over_15_years_unverified_not_violation():
    """Verify missing renewal evidence on 15+ year private vehicle is UNVERIFIED, not assumed expired."""
    result = evaluate_vehicle_safety(
        make="Honda",
        model="Accord",
        year=2006,
        current_year=2024,  # Age = 18 years
        odometer_km=140000.0,
        vehicle_category="M1_passenger_car",
        fitness_certificate_valid=None,  # Missing evidence
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=3.5,
    )
    # Must NOT assume violation
    assert len(result.statutory_violations) == 0
    reg_audit = next(p for p in result.parameter_breakdown if "Registration" in p["parameter"])
    assert reg_audit["status"] == "unverified"
    assert reg_audit["deduction_applied"] == 0.0


def test_private_vehicle_over_15_years_expired_renewal():
    """Verify private vehicle >= 15 years with unrenewed registration is a statutory violation."""
    result = evaluate_vehicle_safety(
        make="Maruti",
        model="800",
        year=2004,
        current_year=2024,
        odometer_km=120000.0,
        vehicle_category="M1_passenger_car",
        fitness_certificate_valid=False,  # Unrenewed
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=3.5,
    )
    assert len(result.statutory_violations) >= 1
    assert "CMVR Rule 52" in result.statutory_violations[0]


def test_commercial_transport_fitness_rule_62():
    """Verify commercial transport vehicle requires fitness certificate under CMVR Rule 62."""
    result = evaluate_vehicle_safety(
        make="Tata",
        model="Ace",
        year=2020,
        odometer_km=80000.0,
        vehicle_category="commercial_transport",
        fitness_certificate_valid=False,
        brake_pad_thickness_mm=5.0,
        tyre_tread_depth_mm=3.5,
    )
    assert len(result.statutory_violations) >= 1
    assert "CMVR Rule 62 & MVA Sec 56" in result.statutory_violations[0]


# ── Step 5: PUC and Insurance Verification Transparency ──────────────────────

def test_puc_and_insurance_states():
    """Verify PUC and insurance compliant, violation, and unverified states."""
    # Compliant (self-reported)
    res_comp = evaluate_vehicle_safety(
        make="Honda",
        model="Amaze",
        year=2021,
        odometer_km=25000.0,
        puc_valid=True,
        insurance_valid=True,
        brake_pad_thickness_mm=6.0,
        tyre_tread_depth_mm=4.0,
    )
    assert res_comp.document_verification_source == "self_reported_unverified"
    puc_audit = next(p for p in res_comp.parameter_breakdown if p["parameter"] == "PUC Certificate")
    assert puc_audit["status"] == "compliant"
    assert "Not verified against Parivahan" in puc_audit["finding"]

    # Expired PUC
    res_puc_bad = evaluate_vehicle_safety(
        make="Honda",
        model="Amaze",
        year=2021,
        odometer_km=25000.0,
        puc_valid=False,
        brake_pad_thickness_mm=6.0,
        tyre_tread_depth_mm=4.0,
    )
    assert any("CMVR Rule 115(7)" in v for v in res_puc_bad.statutory_violations)

    # Missing PUC -> unverified
    res_puc_none = evaluate_vehicle_safety(
        make="Honda",
        model="Amaze",
        year=2021,
        odometer_km=25000.0,
        puc_valid=None,
        brake_pad_thickness_mm=6.0,
        tyre_tread_depth_mm=4.0,
    )
    puc_none_audit = next(p for p in res_puc_none.parameter_breakdown if p["parameter"] == "PUC Certificate")
    assert puc_none_audit["status"] == "unverified"
    assert puc_none_audit["deduction_applied"] == 0.0


# ── Step 6: Standards Registry Endpoint & Disclaimer Version ─────────────────

def test_standards_registry_content():
    """Verify standards registry contains accurate legal references, URLs, and category scopes."""
    assert "cmvr_rule_95" in STANDARDS_REGISTRY
    rule_95 = STANDARDS_REGISTRY["cmvr_rule_95"]
    assert rule_95["thresholds"]["M1_passenger_car"]["statutory_minimum_nsd_mm"] == 1.6
    assert rule_95["thresholds"]["L_two_three_wheeler"]["statutory_minimum_nsd_mm"] == 0.8
    assert "https://morth.nic.in" in rule_95["official_source_url"]

    # Verify OEM brake guidelines clarifies non-statutory nature
    brakes = STANDARDS_REGISTRY["oem_brake_guidelines"]
    assert brakes["category"] == "Advisory Engineering Practice & Manufacturer Service Guideline"
    assert "CMVR Rule 96 regulates stopping performance" in brakes["clarification"]


# ── Step 7: API Endpoints Integration Tests (AsyncClient) ───────────────────

_mock_vehicle_store = {}


class MockVehicleResult:
    def __init__(self, record):
        self._record = record

    def scalar_one_or_none(self):
        return self._record


class MockVehicleSession:
    def __init__(self):
        self._added = []

    def add(self, obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid4()
        if not hasattr(obj, "created_at") or obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        self._added.append(obj)

    async def commit(self):
        for obj in self._added:
            _mock_vehicle_store[str(obj.id)] = obj
        self._added.clear()

    async def refresh(self, obj):
        pass

    async def rollback(self):
        self._added.clear()

    async def execute(self, statement):
        target_id = None
        try:
            if hasattr(statement, "_where_criteria"):
                for criterion in statement._where_criteria:
                    if hasattr(criterion, "right") and hasattr(criterion.right, "value"):
                        target_id = str(criterion.right.value)
                        break
        except Exception:
            pass

        if target_id:
            record = _mock_vehicle_store.get(str(target_id))
            return MockVehicleResult(record)
        return MockVehicleResult(None)


async def _mock_vehicle_get_db():
    yield MockVehicleSession()


@pytest.fixture(autouse=True)
def _override_vehicle_db():
    app.dependency_overrides[get_db] = _mock_vehicle_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    _mock_vehicle_store.clear()


@pytest.mark.asyncio
async def test_disclaimer_acknowledgement_required():
    """Verify HTTP 422 is returned when disclaimer_acknowledged is False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Toyota",
                "model": "Yaris",
                "year": 2019,
                "odometer_km": 40000.0,
                "vehicle_category": "M1_passenger_car",
                "brake_pad_thickness_mm": 5.0,
                "tyre_tread_depth_mm": 3.0,
                "disclaimer_acknowledged": False,  # Rejected
            },
        )
        assert response.status_code == 422
        assert "acknowledgement" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_and_get_vehicle_assessment_api():
    """Verify end-to-end POST /assess and GET /{id} flow with category and document metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Post new assessment
        post_res = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Tata",
                "model": "Harrier",
                "year": 2021,
                "odometer_km": 35000.0,
                "vehicle_category": "M1_passenger_car",
                "brake_pad_thickness_mm": 6.5,
                "tyre_tread_depth_mm": 4.8,
                "service_records_count": 3,
                "past_accidents_count": 0,
                "puc_valid": True,
                "insurance_valid": True,
                "disclaimer_acknowledged": True,
            },
        )
        assert post_res.status_code == 201
        data = post_res.json()
        assert data["make"] == "Tata"
        assert data["vehicle_category"] == "M1_passenger_car"
        assert data["risk_tier"] == "Low"
        assert data["document_verification_source"] == "self_reported_unverified"
        assert len(data["parameter_breakdown"]) > 0

        assessment_id = data["id"]

        # 2. Retrieve assessment by ID
        get_res = await client.get(f"/api/v1/vehicles/{assessment_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == assessment_id
        assert get_data["vehicle_category"] == "M1_passenger_car"


@pytest.mark.asyncio
async def test_get_vehicle_assessment_not_found():
    """Verify HTTP 404 for non-existent vehicle assessment ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/vehicles/{uuid4()}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_standards_api_endpoint():
    """Verify GET /api/v1/vehicles/standards returns registry and version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/vehicles/standards")
        assert response.status_code == 200
        data = response.json()
        assert "standards" in data
        assert "cmvr_rule_95" in data["standards"]
        assert "version" in data


# ── Step 8: Additional Boundary, Integrity & Failure Mode Tests ─────────────

def test_m1_passenger_car_tyre_advisory_boundary():
    """Verify passenger car tyre advisory boundary at 2.49 mm (warning) vs 2.50 mm (compliant)."""
    # 2.49 mm -> advisory warning
    res_warn = evaluate_vehicle_safety(
        make="Hyundai",
        model="Verna",
        year=2021,
        odometer_km=25000.0,
        vehicle_category="M1_passenger_car",
        tyre_tread_depth_mm=2.49,
    )
    tyre_audit_warn = next(p for p in res_warn.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit_warn["status"] == "warning"
    assert tyre_audit_warn["deduction_applied"] == 18.0

    # 2.50 mm -> compliant (moderate wear)
    res_comp = evaluate_vehicle_safety(
        make="Hyundai",
        model="Verna",
        year=2021,
        odometer_km=25000.0,
        vehicle_category="M1_passenger_car",
        tyre_tread_depth_mm=2.50,
    )
    tyre_audit_comp = next(p for p in res_comp.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert tyre_audit_comp["status"] == "compliant"
    assert tyre_audit_comp["deduction_applied"] == 6.0


def test_l_two_wheeler_tyre_boundary_above_and_advisory():
    """Verify Category L tyre at 0.81 mm (warning) vs 1.49 mm (warning) vs 1.50 mm (compliant)."""
    # 0.81 mm -> legally compliant but in advisory wear window (< 1.5 mm)
    res_81 = evaluate_vehicle_safety(
        make="TVS",
        model="Apache",
        year=2022,
        odometer_km=12000.0,
        vehicle_category="L_two_three_wheeler",
        tyre_tread_depth_mm=0.81,
    )
    assert len(res_81.statutory_violations) == 0
    t81 = next(p for p in res_81.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert t81["status"] == "warning"

    # 1.50 mm -> out of advisory wear window
    res_150 = evaluate_vehicle_safety(
        make="TVS",
        model="Apache",
        year=2022,
        odometer_km=12000.0,
        vehicle_category="L_two_three_wheeler",
        tyre_tread_depth_mm=1.50,
    )
    t150 = next(p for p in res_150.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert t150["status"] == "compliant"


def test_unknown_vehicle_category_below_and_above_all_limits():
    """Verify unknown category with <0.8 mm is illegal for all, and >=1.6 mm is compliant for all."""
    # < 0.8 mm -> statutory violation for all motor vehicles
    res_viol = evaluate_vehicle_safety(
        make="Unknown",
        model="Model",
        year=2020,
        odometer_km=30000.0,
        vehicle_category="unknown",
        tyre_tread_depth_mm=0.75,
    )
    assert len(res_viol.statutory_violations) == 1
    assert "illegal for ALL vehicle categories" in res_viol.statutory_violations[0]

    # >= 1.6 mm -> compliant for all motor vehicles
    res_comp = evaluate_vehicle_safety(
        make="Unknown",
        model="Model",
        year=2020,
        odometer_km=30000.0,
        vehicle_category="unknown",
        tyre_tread_depth_mm=1.65,
    )
    assert len(res_comp.statutory_violations) == 0
    t_audit = next(p for p in res_comp.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert t_audit["status"] == "compliant"


def test_missing_vehicle_category_resolves_to_unknown():
    """Verify omitted or None vehicle category defaults to UNKNOWN, not passenger car."""
    res = evaluate_vehicle_safety(
        make="Custom",
        model="Special",
        year=2020,
        odometer_km=20000.0,
        vehicle_category=None,  # Missing
        tyre_tread_depth_mm=1.2,
    )
    assert res.vehicle_category == VehicleCategory.UNKNOWN.value
    t_audit = next(p for p in res.parameter_breakdown if p["parameter"] == "Tyre Tread Depth")
    assert t_audit["status"] == "unverified"


def test_missing_running_gear_elevates_risk_tier():
    """Verify that when tyre and brake measurements are missing, vehicle cannot be rated Low risk."""
    res = evaluate_vehicle_safety(
        make="Honda",
        model="City",
        year=2022,
        odometer_km=15000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=None,  # Missing
        tyre_tread_depth_mm=None,     # Missing
        puc_valid=True,
        insurance_valid=True,
    )
    # Even with high score from other factors, missing running gear must not be rated 'Low'
    assert res.risk_tier != "Low"
    assert res.risk_tier == "Moderate"
    assert any("UNVERIFIED RUNNING GEAR ADVISORY" in w for w in res.advisory_warnings)


def test_missing_measurements_never_downgrade_critical_statutory_violation():
    """Verify missing brake evidence NEVER downgrades a confirmed statutory tyre violation."""
    res = evaluate_vehicle_safety(
        make="Tata",
        model="Nexon",
        year=2021,
        odometer_km=30000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=None,  # Missing
        tyre_tread_depth_mm=1.2,     # Confirmed statutory violation (< 1.6 mm)
        puc_valid=True,
        insurance_valid=True,
    )
    # Must remain Critical regardless of missing brake measurement
    assert res.risk_tier == "Critical"
    assert res.preliminary_score <= 35.0
    assert len(res.statutory_violations) >= 1
    assert any("CMVR Rule 95" in v for v in res.statutory_violations)


def test_missing_measurements_never_downgrade_critical_brake_wear():
    """Verify missing tyre evidence NEVER downgrades a confirmed critical brake wear hazard."""
    res = evaluate_vehicle_safety(
        make="Hyundai",
        model="Creta",
        year=2020,
        odometer_km=40000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=1.5,  # Confirmed critical discard (< 2.0 mm)
        tyre_tread_depth_mm=None,    # Missing
        puc_valid=True,
        insurance_valid=True,
    )
    # Must remain Critical due to severe mechanical hazard
    assert res.risk_tier == "Critical"
    assert res.preliminary_score <= 35.0
    assert len(res.critical_warnings) >= 1
    assert any("Manufacturer Discard Guideline" in w for w in res.critical_warnings)
    # But brake wear alone is advisory OEM, NOT a false statutory violation
    assert len(res.statutory_violations) == 0


def test_single_missing_measurement_caps_tier_at_moderate():
    """Verify vehicle with one missing measurement and otherwise pristine condition is capped at Moderate."""
    res = evaluate_vehicle_safety(
        make="Toyota",
        model="Camry",
        year=2023,
        odometer_km=10000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=8.0,  # Compliant
        tyre_tread_depth_mm=None,    # Missing tyre depth
        puc_valid=True,
        insurance_valid=True,
    )
    assert res.preliminary_score == 100.0
    assert res.risk_tier == "Moderate"
    assert any("UNVERIFIED TYRE ADVISORY" in w for w in res.advisory_warnings)


def test_advisory_findings_combined_with_missing_measurements():
    """Verify advisory findings and missing measurements combine consistently without contradictions."""
    res = evaluate_vehicle_safety(
        make="Maruti",
        model="Baleno",
        year=2021,
        odometer_km=25000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=None,  # Missing brake measurement
        tyre_tread_depth_mm=2.0,      # Advisory wear window (1.6 to 2.5 mm, -18 deduction)
        puc_valid=True,
        insurance_valid=True,
    )
    assert res.preliminary_score == 82.0
    assert res.risk_tier == "Moderate"
    assert len(res.statutory_violations) == 0
    # Both tyre advisory warning and unverified brake advisory should be recorded
    assert any("ADVISORY WARNING" in w for w in res.advisory_warnings)
    assert any("UNVERIFIED BRAKE ADVISORY" in w for w in res.advisory_warnings)


def test_commercial_transport_fitness_valid_and_missing():
    """Verify commercial transport fitness valid and unverified states."""
    # Valid
    res_valid = evaluate_vehicle_safety(
        make="Ashok Leyland",
        model="Dost",
        year=2021,
        odometer_km=60000.0,
        vehicle_category="commercial_transport",
        fitness_certificate_valid=True,
    )
    assert len(res_valid.statutory_violations) == 0
    fit_audit = next(p for p in res_valid.parameter_breakdown if "Commercial Fitness" in p["parameter"])
    assert fit_audit["status"] == "compliant"

    # Missing (None)
    res_missing = evaluate_vehicle_safety(
        make="Ashok Leyland",
        model="Dost",
        year=2021,
        odometer_km=60000.0,
        vehicle_category="commercial_transport",
        fitness_certificate_valid=None,
    )
    assert len(res_missing.statutory_violations) == 0
    fit_missing = next(p for p in res_missing.parameter_breakdown if "Commercial Fitness" in p["parameter"])
    assert fit_missing["status"] == "unverified"
    assert fit_missing["deduction_applied"] == 0.0


def test_unknown_category_fitness_unverified():
    """Verify unknown category fitness check returns UNVERIFIED rather than guessing private or commercial."""
    res = evaluate_vehicle_safety(
        make="Fleet",
        model="Unit",
        year=2020,
        odometer_km=50000.0,
        vehicle_category="unknown",
        fitness_certificate_valid=None,
    )
    fit_audit = next(p for p in res.parameter_breakdown if "Registration / Fitness" in p["parameter"])
    assert fit_audit["status"] == "unverified"
    assert "Vehicle category is unknown" in fit_audit["finding"]


def test_score_and_severity_caps_consistency():
    """Verify score is capped at <= 35.0 and tier is Critical when statutory violations exist."""
    # Statutory tyre violation
    res = evaluate_vehicle_safety(
        make="Hyundai",
        model="Creta",
        year=2023,
        odometer_km=10000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=9.0,
        tyre_tread_depth_mm=1.0,  # Below 1.6 mm limit
        service_records_count=5,
        past_accidents_count=0,
        puc_valid=True,
        insurance_valid=True,
    )
    assert res.preliminary_score <= 35.0
    assert res.risk_tier == "Critical"
    assert len(res.statutory_violations) >= 1

    # Critical brake wear (< 2.0 mm)
    res_brake = evaluate_vehicle_safety(
        make="Hyundai",
        model="Creta",
        year=2023,
        odometer_km=10000.0,
        vehicle_category="M1_passenger_car",
        brake_pad_thickness_mm=1.5,  # Below 2.0 mm discard limit
        tyre_tread_depth_mm=6.0,
        puc_valid=True,
        insurance_valid=True,
    )
    assert res_brake.preliminary_score <= 35.0
    assert res_brake.risk_tier == "Critical"
    assert len(res_brake.critical_warnings) >= 1
    assert len(res_brake.statutory_violations) == 0  # Not a statutory violation!


@pytest.mark.asyncio
async def test_invalid_request_payload_values():
    """Verify API returns 422 for invalid parameter values (negative odometer, tyre > 20 mm, etc.)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Negative odometer
        res_odo = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Toyota",
                "model": "Yaris",
                "year": 2020,
                "odometer_km": -500.0,
                "disclaimer_acknowledged": True,
            },
        )
        assert res_odo.status_code == 422

        # Negative tyre tread depth
        res_tyre = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Toyota",
                "model": "Yaris",
                "year": 2020,
                "odometer_km": 10000.0,
                "tyre_tread_depth_mm": -1.0,
                "disclaimer_acknowledged": True,
            },
        )
        assert res_tyre.status_code == 422

        # Unrealistic tyre tread depth (> 20.0 mm)
        res_big_tyre = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Toyota",
                "model": "Yaris",
                "year": 2020,
                "odometer_km": 10000.0,
                "tyre_tread_depth_mm": 55.0,
                "disclaimer_acknowledged": True,
            },
        )
        assert res_big_tyre.status_code == 422


@pytest.mark.asyncio
async def test_post_assessment_with_nullable_missing_measurements():
    """Verify POST /assess persists cleanly when tyre and brake measurements are None."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/vehicles/assess",
            json={
                "make": "Maruti",
                "model": "Alto",
                "year": 2019,
                "odometer_km": 42000.0,
                "brake_pad_thickness_mm": None,
                "tyre_tread_depth_mm": None,
                "disclaimer_acknowledged": True,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["brake_pad_thickness_mm"] is None
        assert data["tyre_tread_depth_mm"] is None
        assert data["id"] is not None

        # Verify retrieval of record with null fields
        get_res = await client.get(f"/api/v1/vehicles/{data['id']}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["brake_pad_thickness_mm"] is None
        assert get_data["tyre_tread_depth_mm"] is None
