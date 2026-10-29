"""Comprehensive test suite for Phase 5.3: Hospital & Emergency Proximity Support.

Tests:
1. Coordinate and query parameter bounds validation (latitude, longitude, radius, limit -> 422).
2. Spatial proximity filtering (inside vs. outside search radius).
3. Emergency-service filtering (emergency_only=True excludes non-emergency facilities).
4. Distance ordering (closest to farthest ascending).
5. Empty result handling (distinguishing zero facilities from service errors).
6. PostGIS vs. Haversine fallback engine accuracy and diagnostics.
7. Database connection failure propagation (returns 503 instead of masking errors).
8. Single hospital retrieval by ID (valid -> 200, not found -> 404, invalid UUID -> 422).
"""
import math
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from geoalchemy2.elements import WKTElement

from app.main import app
from app.core.database import get_db
from app.core.spatial import (
    haversine_distance_meters,
    bounding_box_for_radius,
    spatial_service,
    SpatialServiceUnavailableError,
)
from app.models.hospital import Hospital
from app.schemas.hospital import NearbyHospitalsResponse, HospitalRead


class MockHospitalRecord:
    """Mock Hospital model instance for spatial test queries."""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.name = kwargs.get("name", "Test General Hospital")
        self.facility_type = kwargs.get("facility_type", "General Hospital")
        self.latitude = float(kwargs.get("latitude", 12.9716))
        self.longitude = float(kwargs.get("longitude", 77.5946))
        self.geom = kwargs.get("geom", WKTElement(f"POINT({self.longitude} {self.latitude})", srid=4326))
        self.address = kwargs.get("address", "123 Main Road, Bengaluru")
        self.contact_phone = kwargs.get("contact_phone", "+91-80-12345678")
        self.has_emergency_service = kwargs.get("has_emergency_service", True)
        self.total_beds_reference = kwargs.get("total_beds_reference", 250)
        self.is_verified_facility = kwargs.get("is_verified_facility", True)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))


_hospital_store: list[MockHospitalRecord] = []
_simulate_db_failure: bool = False


class MockHospitalScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._items[0] if self._items else None


class MockHospitalAsyncSession:
    """Mock session providing filtered hospital records or simulating failure."""
    async def execute(self, query):
        if _simulate_db_failure:
            raise ConnectionError("Simulated database failure during hospital query")

        q_str = str(query).lower()

        # Handle single hospital by ID query
        if "where hospitals.id =" in q_str or "hospitals.id = :" in q_str or "hospitals.id" in q_str:
            # Check if this is an ID lookup
            for h in _hospital_store:
                if str(h.id).lower() in q_str:
                    return MockHospitalScalarResult([h])

        # Filter by emergency service if requested in query WHERE clause
        candidates = list(_hospital_store)
        where_part = q_str[q_str.find("where"):] if "where" in q_str else ""
        if "has_emergency_service" in where_part:
            candidates = [h for h in candidates if h.has_emergency_service]

        # Default query for proximity candidates
        return MockHospitalScalarResult(candidates)

    async def close(self):
        pass


async def _mock_hospital_get_db():
    session = MockHospitalAsyncSession()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture(autouse=True)
def _setup_hospital_test():
    global _simulate_db_failure
    _hospital_store.clear()
    _simulate_db_failure = False
    prior_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _mock_hospital_get_db
    yield
    _hospital_store.clear()
    _simulate_db_failure = False
    if prior_override:
        app.dependency_overrides[get_db] = prior_override
    else:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 1. Parameter Validation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_missing_coords():
    """Missing latitude or longitude returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/hospitals/nearby")
        assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "lat,lon,expected_status",
    [
        (95.0, 77.5946, 422),     # Lat > 90
        (-95.0, 77.5946, 422),    # Lat < -90
        (12.9716, 185.0, 422),    # Lon > 180
        (12.9716, -185.0, 422),   # Lon < -180
        (12.9716, 77.5946, 200),  # Valid
    ],
)
async def test_nearby_hospitals_coordinate_bounds(lat, lon, expected_status):
    """Coordinates outside valid WGS84 bounds are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hospitals/nearby?latitude={lat}&longitude={lon}&radius_meters=1000"
        )
        assert resp.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "radius,expected_status",
    [
        (50.0, 422),       # Below minimum 100m
        (0.0, 422),        # Zero radius
        (-500.0, 422),     # Negative radius
        (150000.0, 422),   # Above maximum 100,000m (100km)
        (100.0, 200),      # Minimum boundary
        (5000.0, 200),     # Typical 5km
        (100000.0, 200),   # Maximum boundary
    ],
)
async def test_nearby_hospitals_radius_bounds(radius, expected_status):
    """Radius outside [100, 100,000] meters is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hospitals/nearby?latitude=12.9716&longitude=77.5946&radius_meters={radius}"
        )
        assert resp.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit,expected_status",
    [
        (0, 422),    # Below minimum
        (-5, 422),   # Negative
        (101, 422),  # Above maximum 100
        (1, 200),    # Valid min
        (20, 200),   # Valid default
        (100, 200),  # Valid max
    ],
)
async def test_nearby_hospitals_limit_bounds(limit, expected_status):
    """Limit outside [1, 100] is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hospitals/nearby?latitude=12.9716&longitude=77.5946&limit={limit}"
        )
        assert resp.status_code == expected_status


# ==============================================================================
# 2. Proximity and Radius Filtering Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_proximity_filtering():
    """Facilities inside search radius are included; outside are excluded."""
    center_lat, center_lon = 12.9716, 77.5946

    # Hospital A: ~800m away (inside 5km radius)
    hosp_near = MockHospitalRecord(
        name="Nearby Trauma Care",
        facility_type="Trauma Center",
        latitude=12.9750,
        longitude=77.5980,
        has_emergency_service=True,
    )
    # Hospital B: ~3.5km away (inside 5km radius)
    hosp_mid = MockHospitalRecord(
        name="Midrange General Hospital",
        facility_type="General Hospital",
        latitude=12.9450,
        longitude=77.5946,
        has_emergency_service=True,
    )
    # Hospital C: ~25km away (outside 5km radius)
    hosp_far = MockHospitalRecord(
        name="Distant Hospital",
        facility_type="Super Specialty",
        latitude=13.1500,
        longitude=77.6000,
        has_emergency_service=True,
    )

    _hospital_store.extend([hosp_near, hosp_mid, hosp_far])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hospitals/nearby?latitude={center_lat}&longitude={center_lon}&radius_meters=5000"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_found"] == 2
        names = [h["name"] for h in data["hospitals"]]
        assert "Nearby Trauma Care" in names
        assert "Midrange General Hospital" in names
        assert "Distant Hospital" not in names


# ==============================================================================
# 3. Emergency Service Filtering Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_emergency_only_filter():
    """emergency_only=True excludes facilities without 24/7 casualty emergency triage."""
    center_lat, center_lon = 12.9716, 77.5946

    hosp_emergency = MockHospitalRecord(
        name="24/7 Trauma Emergency Center",
        latitude=12.9720,
        longitude=77.5950,
        has_emergency_service=True,
    )
    hosp_clinic = MockHospitalRecord(
        name="Daytime Outpatient Polyclinic",
        latitude=12.9725,
        longitude=77.5955,
        has_emergency_service=False,
    )

    _hospital_store.extend([hosp_emergency, hosp_clinic])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without filter: both returned
        resp_all = await client.get(
            f"/api/v1/hospitals/nearby?latitude={center_lat}&longitude={center_lon}&radius_meters=5000&emergency_only=false"
        )
        assert resp_all.status_code == 200
        assert resp_all.json()["total_found"] == 2

        # With emergency_only=true: only emergency facility returned
        resp_em = await client.get(
            f"/api/v1/hospitals/nearby?latitude={center_lat}&longitude={center_lon}&radius_meters=5000&emergency_only=true"
        )
        assert resp_em.status_code == 200
        data_em = resp_em.json()
        assert data_em["total_found"] == 1
        assert data_em["hospitals"][0]["name"] == "24/7 Trauma Emergency Center"


# ==============================================================================
# 4. Distance Ordering Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_distance_ordering():
    """Hospitals are returned in ascending order of straight-line distance."""
    center_lat, center_lon = 12.9716, 77.5946

    h_close = MockHospitalRecord(name="Closest", latitude=12.9720, longitude=77.5946)
    h_mid = MockHospitalRecord(name="Middle", latitude=12.9800, longitude=77.5946)
    h_far = MockHospitalRecord(name="Farthest", latitude=12.9950, longitude=77.5946)

    # Insert in scrambled order
    _hospital_store.extend([h_far, h_close, h_mid])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hospitals/nearby?latitude={center_lat}&longitude={center_lon}&radius_meters=10000"
        )
        assert resp.status_code == 200
        data = resp.json()

        distances = [h["straight_line_distance_meters"] for h in data["hospitals"]]
        assert distances == sorted(distances)
        assert data["hospitals"][0]["name"] == "Closest"
        assert data["hospitals"][-1]["name"] == "Farthest"


# ==============================================================================
# 5. Empty Dataset Handling Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_empty_result():
    """When no facilities are found, returns 200 with total_found=0 and helpful advisory."""
    _hospital_store.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/hospitals/nearby?latitude=12.9716&longitude=77.5946&radius_meters=5000"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_found"] == 0
        assert data["hospitals"] == []
        assert "112" in data["emergency_helplines_india"]["National Emergency Number"]
        assert "108" in data["emergency_helplines_india"]["Ambulance / Medical Emergency"]
        assert "EMERGENCY NOTICE" in data["disclaimer"]
        assert any("No verified hospital facilities found" in note for note in data["advisory_notes"])


# ==============================================================================
# 6. Fallback and Spatial Engine Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_haversine_engine():
    """Querying via Haversine calculation returns valid distance and engine metadata."""
    session = MockHospitalAsyncSession()
    hosp = MockHospitalRecord(
        name="Victoria Hospital",
        latitude=12.9634,
        longitude=77.5746,
        has_emergency_service=True,
    )
    _hospital_store.append(hosp)

    res = await spatial_service.query_nearby_hospitals(
        db=session,
        latitude=12.9716,
        longitude=77.5946,
        radius_meters=5000.0,
        emergency_only=False,
        force_engine="haversine",
    )

    assert isinstance(res, NearbyHospitalsResponse)
    assert res.spatial_engine == "haversine_fallback"
    assert res.total_found == 1
    item = res.hospitals[0]
    assert item.name == "Victoria Hospital"
    assert item.straight_line_distance_km > 0.0
    assert item.straight_line_distance_meters > 0.0


# ==============================================================================
# 7. Database Connection Failure Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_nearby_hospitals_db_failure_propagates_503():
    """Database connection failure is returned as 503 Service Unavailable, not masked."""
    global _simulate_db_failure
    _simulate_db_failure = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/hospitals/nearby?latitude=12.9716&longitude=77.5946&radius_meters=5000"
        )
        assert resp.status_code == 503
        data = resp.json()
        assert "detail" in data


# ==============================================================================
# 8. Single Hospital Lookup Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_get_hospital_by_id_success():
    """Existing hospital UUID returns 200 with complete HospitalRead payload."""
    h_id = uuid4()
    hosp = MockHospitalRecord(
        id=h_id,
        name="Bowring and Lady Curzon",
        facility_type="Super Specialty",
        latitude=12.9830,
        longitude=77.6046,
        address="Lady Curzon Road, Bengaluru",
        contact_phone="+91-80-25591325",
        total_beds_reference=686,
    )
    _hospital_store.append(hosp)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/hospitals/{h_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["id"] == str(h_id)
        assert data["name"] == "Bowring and Lady Curzon"
        assert data["facility_type"] == "Super Specialty"
        assert data["total_beds_reference"] == 686
        assert data["contact_phone"] == "+91-80-25591325"


@pytest.mark.asyncio
async def test_get_hospital_by_id_not_found():
    """Non-existent UUID returns 404 with descriptive detail."""
    random_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/hospitals/{random_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert f"'{random_id}'" in data["detail"]


@pytest.mark.asyncio
async def test_get_hospital_by_id_invalid_uuid():
    """Malformed non-UUID path parameter returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/hospitals/not-a-valid-uuid")
        assert resp.status_code == 422
