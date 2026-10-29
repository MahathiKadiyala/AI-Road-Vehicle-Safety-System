"""Comprehensive test suite for Phase 5.1: PostGIS Hazard Geometry and Spatial Density.

Tests:
1. Coordinate and radius validation (422 checks on lat/lon/radius limits).
2. PostGIS POINT WKT coordinate ordering (X=longitude, Y=latitude, SRID 4326).
3. Hazards within vs. outside the search radius (precise boundary filtering).
4. Empty result sets (distinguishing valid 0-hazard areas from service failure).
5. Missing geometry handling and diagnostic counts.
6. Haversine distance mathematical accuracy against known geographic points.
7. PostGIS-unavailable behavior and graceful Haversine fallback.
8. Database connection failure propagation (ensuring failures are not masked as 0).
"""
import math
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from geoalchemy2.elements import WKTElement

from app.main import app
from app.core.database import get_db
from app.core.spatial import (
    create_point_geometry,
    haversine_distance_meters,
    bounding_box_for_radius,
    spatial_service,
    SpatialServiceUnavailableError,
)
from app.models.hazard import Hazard
from app.schemas.hazard import HazardDensityResponse


class MockDensityHazard:
    """Mock Hazard record for spatial query simulation."""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.title = kwargs.get("title", "Test Hazard")
        self.hazard_type = kwargs.get("hazard_type", "pothole")
        self.severity = kwargs.get("severity", "medium")
        self.latitude = float(kwargs.get("latitude", 12.9716))
        self.longitude = float(kwargs.get("longitude", 77.5946))
        self.geom = kwargs.get("geom", None)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))


_density_store: list[MockDensityHazard] = []


class MockScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def scalars(self):
        return self

    def scalar(self):
        return self._items[0] if self._items else None


class MockDensityAsyncSession:
    """Mock session providing filtered hazards based on bounding box or scalar queries."""
    async def execute(self, query):
        q_str = str(query).lower()

        # Handle missing geometry count query
        if "count" in q_str and "geom is null" in q_str:
            missing = sum(1 for h in _density_store if h.geom is None)
            return MockScalarResult([missing])

        # Handle bounding box or general select
        return MockScalarResult(list(_density_store))

    async def close(self):
        pass


async def _mock_density_get_db():
    session = MockDensityAsyncSession()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture(autouse=True)
def _setup_density_store():
    _density_store.clear()
    app.dependency_overrides[get_db] = _mock_density_get_db
    yield
    _density_store.clear()
    app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 1. Coordinate Ordering & Geometry Creation Tests
# ==============================================================================

def test_create_point_geometry_ordering_and_srid():
    """Verify PostGIS WKT POINT geometry: X=longitude, Y=latitude, SRID=4326."""
    lat = 12.9716
    lon = 77.5946

    elem = create_point_geometry(latitude=lat, longitude=lon)
    assert isinstance(elem, WKTElement)
    assert elem.srid == 4326
    # OGC/PostGIS POINT format: POINT(X Y) -> POINT(lon lat)
    assert elem.data == f"POINT({lon} {lat})"


def test_create_point_geometry_bounds_validation():
    """Verify bounds checking on coordinates."""
    with pytest.raises(ValueError, match="Latitude out of bounds"):
        create_point_geometry(latitude=90.1, longitude=77.5)

    with pytest.raises(ValueError, match="Latitude out of bounds"):
        create_point_geometry(latitude=-90.1, longitude=77.5)

    with pytest.raises(ValueError, match="Longitude out of bounds"):
        create_point_geometry(latitude=12.9, longitude=180.1)

    with pytest.raises(ValueError, match="Longitude out of bounds"):
        create_point_geometry(latitude=12.9, longitude=-180.1)


# ==============================================================================
# 2. Haversine Math & Bounding Box Tests
# ==============================================================================

def test_haversine_distance_meters_known_coordinates():
    """Verify great-circle distance computation against known geographic measurements."""
    # Bangalore center: (12.9716, 77.5946)
    # Point ~62m away: (12.9720, 77.5950)
    d1 = haversine_distance_meters(12.9716, 77.5946, 12.9720, 77.5950)
    assert 60.0 < d1 < 65.0

    # Same location must be 0m
    d0 = haversine_distance_meters(12.9716, 77.5946, 12.9716, 77.5946)
    assert d0 == 0.0

    # 1 degree of latitude north at equator is approx 111,195m
    d_lat = haversine_distance_meters(0.0, 0.0, 1.0, 0.0)
    assert 111000.0 < d_lat < 112000.0


def test_bounding_box_for_radius_calculation():
    """Verify bounding box encompasses search radius."""
    lat, lon = 12.9716, 77.5946
    radius_m = 1000.0

    min_lat, max_lat, min_lon, max_lon = bounding_box_for_radius(lat, lon, radius_m)
    assert min_lat < lat < max_lat
    assert min_lon < lon < max_lon

    # Verify that a point at the north edge is within delta_lat
    d_north = haversine_distance_meters(lat, lon, max_lat, lon)
    assert d_north >= radius_m * 0.99


# ==============================================================================
# 3. Endpoint Parameter Validation Tests (GET /hazards/density)
# ==============================================================================

@pytest.mark.asyncio
async def test_hazard_density_endpoint_coordinate_validation():
    """Verify 422 Unprocessable Entity when coordinates or radius are out of bounds."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid latitude (> 90)
        resp1 = await client.get("/api/v1/hazards/density?latitude=91.0&longitude=77.5946")
        assert resp1.status_code == 422

        # Invalid latitude (< -90)
        resp2 = await client.get("/api/v1/hazards/density?latitude=-95.0&longitude=77.5946")
        assert resp2.status_code == 422

        # Invalid longitude (> 180)
        resp3 = await client.get("/api/v1/hazards/density?latitude=12.9716&longitude=185.0")
        assert resp3.status_code == 422

        # Invalid radius (< 10m)
        resp4 = await client.get("/api/v1/hazards/density?latitude=12.9716&longitude=77.5946&radius_meters=5.0")
        assert resp4.status_code == 422

        # Invalid radius (> 50,000m)
        resp5 = await client.get("/api/v1/hazards/density?latitude=12.9716&longitude=77.5946&radius_meters=60000.0")
        assert resp5.status_code == 422


# ==============================================================================
# 4. Nearby Filtering: Within vs. Outside Radius Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_hazard_density_within_and_outside_radius():
    """Verify that hazards outside the search radius are excluded while closer ones are included."""
    center_lat, center_lon = 12.9716, 77.5946

    # Inside 1000m:
    # 1. At center (0m)
    _density_store.append(
        MockDensityHazard(
            title="Pothole at Center",
            hazard_type="pothole",
            severity="critical",
            latitude=12.9716,
            longitude=77.5946,
            geom=create_point_geometry(12.9716, 77.5946),
        )
    )
    # 2. ~62m away
    _density_store.append(
        MockDensityHazard(
            title="Crack Nearby",
            hazard_type="crack",
            severity="medium",
            latitude=12.9720,
            longitude=77.5950,
            geom=create_point_geometry(12.9720, 77.5950),
        )
    )
    # 3. ~823m away
    _density_store.append(
        MockDensityHazard(
            title="Obstacle 800m away",
            hazard_type="obstacle",
            severity="high",
            latitude=12.9790,
            longitude=77.5946,
            geom=create_point_geometry(12.9790, 77.5946),
        )
    )

    # Outside 1000m:
    # 4. ~3150m away (excluded)
    _density_store.append(
        MockDensityHazard(
            title="Far Pothole 3km",
            hazard_type="pothole",
            severity="critical",
            latitude=13.0000,
            longitude=77.5946,
            geom=create_point_geometry(13.0000, 77.5946),
        )
    )
    # 5. ~8700m away (excluded)
    _density_store.append(
        MockDensityHazard(
            title="Very Far Debris 8km",
            hazard_type="debris",
            severity="low",
            latitude=13.0500,
            longitude=77.6000,
            geom=create_point_geometry(13.0500, 77.6000),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/hazards/density?latitude={center_lat}&longitude={center_lon}&radius_meters=1000.0"
        )
        assert resp.status_code == 200
        data = resp.json()

        # Exactly 3 hazards should be inside
        assert data["total_hazards"] == 3
        assert len(data["nearby_hazards"]) == 3

        # Breakdown checks
        assert data["by_type"]["pothole"] == 1
        assert data["by_type"]["crack"] == 1
        assert data["by_type"]["obstacle"] == 1
        assert "debris" not in data["by_type"]

        assert data["by_severity"]["critical"] == 1
        assert data["by_severity"]["medium"] == 1
        assert data["by_severity"]["high"] == 1
        assert data["critical_and_high_count"] == 2  # 1 critical + 1 high

        # Density check: area = pi * (1.0)^2 = ~3.1416 sq km; density = 3 / 3.1416 = 0.95
        assert data["area_sqkm"] == 3.1416
        assert data["density_per_sqkm"] == 0.95

        # Distance ordering check: first hazard should be 0.0m, second ~62.1m, third ~823m
        distances = [h["distance_meters"] for h in data["nearby_hazards"]]
        assert distances == sorted(distances)
        assert distances[0] == 0.0
        assert 60.0 < distances[1] < 65.0


# ==============================================================================
# 5. Empty Result Set Tests (Valid 0 Hazards vs. Failure)
# ==============================================================================

@pytest.mark.asyncio
async def test_hazard_density_empty_results_distinguished():
    """Verify that an area with zero hazards returns 200 OK with 0 counts, not an error."""
    _density_store.clear()  # No hazards

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/hazards/density?latitude=12.9716&longitude=77.5946&radius_meters=1000.0"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_hazards"] == 0
        assert data["density_per_sqkm"] == 0.0
        assert data["by_type"] == {}
        assert data["by_severity"] == {}
        assert data["critical_and_high_count"] == 0
        assert data["nearby_hazards"] == []
        assert data["center_latitude"] == 12.9716
        assert data["center_longitude"] == 77.5946


# ==============================================================================
# 6. Missing Geometry Reporting Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_hazard_density_missing_geometry_handling():
    """Verify that records with geom=None are counted and analyzed via Haversine."""
    # Add a hazard with missing geometry
    _density_store.append(
        MockDensityHazard(
            title="Legacy Unbackfilled Pothole",
            hazard_type="pothole",
            severity="high",
            latitude=12.9720,
            longitude=77.5950,
            geom=None,  # Missing geometry
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/hazards/density?latitude=12.9716&longitude=77.5946&radius_meters=1000.0"
        )
        assert resp.status_code == 200
        data = resp.json()

        # Should find the hazard via Haversine calculation
        assert data["total_hazards"] == 1
        assert data["hazards_with_missing_geometry_count"] == 1
        # Advisory notes should mention legacy records
        assert any("without PostGIS geometry" in note for note in data["advisory_notes"])


# ==============================================================================
# 7. Database Connection Failure Propagation (No Zero Masking)
# ==============================================================================

@pytest.mark.asyncio
async def test_hazard_density_database_error_propagates_503():
    """Verify that database errors are NOT masked as zero hazards, returning HTTP 503."""
    class FailingSession:
        async def execute(self, query):
            raise Exception("connection to server on socket failed: Connection refused")

    async def _failing_get_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = _failing_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/hazards/density?latitude=12.9716&longitude=77.5946&radius_meters=1000.0"
        )
        assert resp.status_code == 503
        data = resp.json()
        assert "unavailable" in data["detail"].lower()


# ==============================================================================
# 8. PostGIS Engine Specific Mapping & Force Engine Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_spatial_service_postgis_row_mapping():
    """Verify PostGIS query path parsing and distance assignment."""
    mock_h = MockDensityHazard(
        title="PostGIS Pothole",
        hazard_type="pothole",
        severity="critical",
        latitude=12.9716,
        longitude=77.5946,
        geom=create_point_geometry(12.9716, 77.5946),
    )

    class PostGISResult:
        def all(self):
            # PostGIS query returns (Hazard, distance_meters) tuples
            return [(mock_h, 45.2)]

    class PostGISSession:
        async def execute(self, query):
            q_str = str(query).lower()
            if "count" in q_str:
                return MockScalarResult([0])
            return PostGISResult()

    res = await spatial_service.query_hazard_density(
        db=PostGISSession(),
        latitude=12.9716,
        longitude=77.5946,
        radius_meters=1000.0,
    )
    assert res.spatial_engine == "postgis"
    assert res.total_hazards == 1
    assert res.by_type["pothole"] == 1
    assert res.by_severity["critical"] == 1
    assert res.nearby_hazards[0].distance_meters == 45.2


@pytest.mark.asyncio
async def test_spatial_service_forced_postgis_failure_raises():
    """Verify that force_engine='postgis' does not fallback to Haversine on PostGIS failure."""
    class FailingPostGISSession:
        async def execute(self, query):
            q_str = str(query).lower()
            if "count" in q_str:
                return MockScalarResult([0])
            raise Exception("function st_dwithin does not exist")

    with pytest.raises(SpatialServiceUnavailableError, match="PostGIS query failed"):
        await spatial_service.query_hazard_density(
            db=FailingPostGISSession(),
            latitude=12.9716,
            longitude=77.5946,
            radius_meters=1000.0,
            force_engine="postgis",
        )


@pytest.mark.asyncio
async def test_spatial_service_forced_haversine_engine():
    """Verify that force_engine='haversine' directly executes Haversine query path."""
    _density_store.append(
        MockDensityHazard(
            title="Haversine Hazard",
            hazard_type="crack",
            severity="low",
            latitude=12.9716,
            longitude=77.5946,
        )
    )

    res = await spatial_service.query_hazard_density(
        db=MockDensityAsyncSession(),
        latitude=12.9716,
        longitude=77.5946,
        radius_meters=1000.0,
        force_engine="haversine",
    )
    assert res.spatial_engine == "haversine_fallback"
    assert res.total_hazards == 1
    assert res.by_type["crack"] == 1
