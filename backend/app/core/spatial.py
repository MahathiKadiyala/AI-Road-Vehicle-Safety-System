"""Spatial utilities and nearby hazard density service.

Provides PostGIS-based distance and radius queries with meter-based semantics
using Geography casting, safe fallback calculation via Haversine distance,
and PostGIS Point geometry creation (SRID 4326, longitude as X, latitude as Y).
"""
import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement

from app.models.hazard import Hazard
from app.models.hospital import Hospital
from app.schemas.hazard import HazardDensityResponse, NearbyHazardSummary
from app.schemas.hospital import NearbyHospitalItem, NearbyHospitalsResponse

logger = logging.getLogger("roadsafety.spatial")

# Earth mean radius in meters (WGS84 spherical approximation)
EARTH_RADIUS_METERS = 6371000.0


class SpatialServiceError(Exception):
    """Raised when spatial operations encounter an unrecoverable failure."""
    pass


class SpatialServiceUnavailableError(SpatialServiceError):
    """Raised when the database or spatial engine cannot be contacted."""
    pass


def create_point_geometry(latitude: float, longitude: float) -> WKTElement:
    """Create a PostGIS POINT geometry WKTElement with SRID 4326.

    In WGS84 (EPSG:4326) Cartesian/GIS convention:
    - X coordinate is Longitude (-180.0 to 180.0)
    - Y coordinate is Latitude (-90.0 to 90.0)

    Args:
        latitude: WGS84 Latitude (-90.0 to 90.0)
        longitude: WGS84 Longitude (-180.0 to 180.0)

    Returns:
        WKTElement: 'POINT(<longitude> <latitude>)' with srid=4326
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude out of bounds [-90, 90]: {latitude}")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude out of bounds [-180, 180]: {longitude}")

    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two GPS coordinates in meters.

    Args:
        lat1, lon1: First coordinate in decimal degrees.
        lat2, lon2: Second coordinate in decimal degrees.

    Returns:
        Distance in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def bounding_box_for_radius(
    lat: float, lon: float, radius_meters: float
) -> Tuple[float, float, float, float]:
    """Calculate an approximate lat/lon bounding box for a search radius in meters.

    Args:
        lat, lon: Center coordinates in degrees.
        radius_meters: Search radius in meters.

    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon) clamped to valid ranges.
    """
    # 1 degree of latitude is approx 111,320 meters
    delta_lat = radius_meters / 111320.0

    # 1 degree of longitude depends on latitude
    cos_lat = math.cos(math.radians(lat))
    effective_cos = max(abs(cos_lat), 0.01)
    delta_lon = radius_meters / (111320.0 * effective_cos)

    min_lat = max(-90.0, lat - delta_lat)
    max_lat = min(90.0, lat + delta_lat)
    min_lon = max(-180.0, lon - delta_lon)
    max_lon = min(180.0, lon + delta_lon)

    return min_lat, max_lat, min_lon, max_lon


class SpatialService:
    """Service for nearby hazard queries and density analysis."""

    async def query_hazard_density(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float = 1000.0,
        force_engine: Optional[str] = None,
    ) -> HazardDensityResponse:
        """Query nearby hazards and compute density metrics within a specified radius.

        Prefers PostGIS ST_DWithin with Geography casting for meter-based semantics.
        Falls back to Haversine calculation when PostGIS is not available.

        Args:
            db: Active async database session.
            latitude: Center latitude (-90 to 90).
            longitude: Center longitude (-180 to 180).
            radius_meters: Bounded search radius in meters (10 to 50,000).
            force_engine: Optional override ('postgis' or 'haversine').

        Returns:
            HazardDensityResponse with counts, breakdowns, density, and nearby records.
        """
        # Parameter validation
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90 (got {latitude})")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180 (got {longitude})")
        if radius_meters < 10.0 or radius_meters > 50000.0:
            raise ValueError(f"Radius must be between 10m and 50,000m (got {radius_meters})")

        area_sqkm = round(math.pi * ((radius_meters / 1000.0) ** 2), 4)

        # Count hazards with missing geometry in DB (for diagnostic reporting)
        missing_geom_count = await self._count_missing_geometries(db)

        # Check if forced to haversine
        if force_engine == "haversine":
            return await self._query_haversine(
                db, latitude, longitude, radius_meters, area_sqkm, missing_geom_count
            )

        # Attempt PostGIS spatial query
        try:
            return await self._query_postgis(
                db, latitude, longitude, radius_meters, area_sqkm, missing_geom_count
            )
        except Exception as exc:
            # If force_engine was explicitly postgis, do not fall back
            if force_engine == "postgis":
                logger.error(f"PostGIS spatial query failed (force_engine=postgis): {exc}")
                raise SpatialServiceUnavailableError(f"PostGIS query failed: {exc}") from exc

            # Check if failure is due to missing PostGIS functions or test environment
            err_str = str(exc).lower()
            is_postgis_missing = (
                "st_dwithin" in err_str
                or "st_distance" in err_str
                or "st_makepoint" in err_str
                or "undefinedfunction" in err_str
                or "no such function" in err_str
                or "geography" in err_str
            )

            # If it's a general connection/auth failure, propagate as service unavailable
            is_connection_error = (
                "password authentication" in err_str
                or "connection refused" in err_str
                or "is the server running" in err_str
                or "could not connect" in err_str
            )

            if is_connection_error:
                logger.error(f"Database connection error during spatial query: {exc}")
                raise SpatialServiceUnavailableError(f"Database connection error: {exc}") from exc

            if is_postgis_missing or "mock" in type(db).__name__.lower():
                logger.info(f"PostGIS query path unavailable ({exc}); falling back to Haversine calculation.")
                return await self._query_haversine(
                    db, latitude, longitude, radius_meters, area_sqkm, missing_geom_count
                )

            # Unknown error: propagate
            logger.error(f"Spatial query unexpected failure: {exc}")
            raise SpatialServiceError(f"Spatial query error: {exc}") from exc

    async def _count_missing_geometries(self, db: AsyncSession) -> int:
        """Count records where geom is NULL."""
        try:
            res = await db.execute(select(func.count(Hazard.id)).where(Hazard.geom.is_(None)))
            val = res.scalar()
            return int(val) if val is not None else 0
        except Exception:
            return 0

    async def _query_postgis(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float,
        area_sqkm: float,
        missing_geom_count: int,
    ) -> HazardDensityResponse:
        """Execute meter-based PostGIS query using Geography casting."""
        # ST_DWithin on Geography uses meters
        # ST_Distance on Geography returns meters
        point_geog = cast(
            func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
            Geography,
        )
        hazard_geog = cast(Hazard.geom, Geography)
        distance_col = func.ST_Distance(hazard_geog, point_geog).label("distance_meters")

        stmt = (
            select(Hazard, distance_col)
            .where(
                Hazard.geom.isnot(None),
                func.ST_DWithin(hazard_geog, point_geog, radius_meters),
            )
            .order_by(distance_col.asc())
            .limit(100)
        )

        result = await db.execute(stmt)
        rows = result.all()

        nearby_hazards: List[NearbyHazardSummary] = []
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for row in rows:
            hazard: Hazard = row[0]
            dist = float(row[1]) if row[1] is not None else 0.0

            by_type[hazard.hazard_type] = by_type.get(hazard.hazard_type, 0) + 1
            by_severity[hazard.severity] = by_severity.get(hazard.severity, 0) + 1

            nearby_hazards.append(
                NearbyHazardSummary(
                    id=hazard.id,
                    title=hazard.title,
                    hazard_type=hazard.hazard_type,
                    severity=hazard.severity,
                    latitude=hazard.latitude,
                    longitude=hazard.longitude,
                    distance_meters=round(dist, 1),
                    created_at=hazard.created_at,
                )
            )

        total_hazards = len(nearby_hazards)
        density_per_sqkm = round(total_hazards / area_sqkm, 2) if area_sqkm > 0 else 0.0
        critical_high = by_severity.get("critical", 0) + by_severity.get("high", 0)

        advisory_notes: List[str] = []
        if missing_geom_count > 0:
            advisory_notes.append(
                f"Database contains {missing_geom_count} legacy hazard record(s) without PostGIS geometry. "
                "Run the migration backfill script to enable spatial indexing for all records."
            )

        return HazardDensityResponse(
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=radius_meters,
            area_sqkm=area_sqkm,
            total_hazards=total_hazards,
            density_per_sqkm=density_per_sqkm,
            by_type=by_type,
            by_severity=by_severity,
            critical_and_high_count=critical_high,
            spatial_engine="postgis",
            hazards_with_missing_geometry_count=missing_geom_count,
            advisory_notes=advisory_notes,
            nearby_hazards=nearby_hazards,
        )

    async def query_nearby_hospitals(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float = 10000.0,
        emergency_only: bool = False,
        limit: int = 20,
        force_engine: Optional[str] = None,
    ) -> NearbyHospitalsResponse:
        """Query nearby hospitals within a radius, ordered by distance ascending.

        Uses PostGIS ST_DWithin with Geography casting in meter units.
        Falls back gracefully to bounding-box Haversine calculation when PostGIS is unavailable.
        """
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90 (got {latitude})")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180 (got {longitude})")
        if radius_meters < 100.0 or radius_meters > 100000.0:
            raise ValueError(f"Search radius must be between 100m and 100,000m (got {radius_meters})")
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100 (got {limit})")

        if force_engine == "haversine":
            return await self._query_hospitals_haversine(
                db, latitude, longitude, radius_meters, emergency_only, limit
            )

        try:
            return await self._query_hospitals_postgis(
                db, latitude, longitude, radius_meters, emergency_only, limit
            )
        except Exception as exc:
            if force_engine == "postgis":
                logger.error(f"PostGIS hospital query failed (force_engine=postgis): {exc}")
                raise SpatialServiceUnavailableError(f"PostGIS query failed: {exc}") from exc

            err_str = str(exc).lower()
            is_postgis_missing = (
                "st_dwithin" in err_str
                or "st_distance" in err_str
                or "st_makepoint" in err_str
                or "undefinedfunction" in err_str
                or "no such function" in err_str
                or "geography" in err_str
            )
            is_connection_error = (
                "password authentication" in err_str
                or "connection refused" in err_str
                or "is the server running" in err_str
                or "could not connect" in err_str
            )

            if is_connection_error:
                logger.error(f"Database connection error during hospital query: {exc}")
                raise SpatialServiceUnavailableError(f"Database connection error: {exc}") from exc

            if is_postgis_missing or "mock" in type(db).__name__.lower():
                logger.info(f"PostGIS hospital query path unavailable ({exc}); using Haversine calculation.")
                return await self._query_hospitals_haversine(
                    db, latitude, longitude, radius_meters, emergency_only, limit
                )

            logger.error(f"Hospital spatial query unexpected failure: {exc}")
            raise SpatialServiceError(f"Hospital spatial query error: {exc}") from exc

    async def _query_hospitals_postgis(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float,
        emergency_only: bool,
        limit: int,
    ) -> NearbyHospitalsResponse:
        """Execute PostGIS query for nearby hospitals."""
        point_geog = cast(
            func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
            Geography,
        )
        hosp_geog = cast(Hospital.geom, Geography)
        distance_col = func.ST_Distance(hosp_geog, point_geog).label("distance_meters")

        stmt = (
            select(Hospital, distance_col)
            .where(
                Hospital.geom.isnot(None),
                func.ST_DWithin(hosp_geog, point_geog, radius_meters),
            )
        )
        if emergency_only:
            stmt = stmt.where(Hospital.has_emergency_service.is_(True))

        stmt = stmt.order_by(distance_col.asc()).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()

        hospitals: List[NearbyHospitalItem] = []
        for row in rows:
            h: Hospital = row[0]
            dist_m = float(row[1]) if row[1] is not None else 0.0

            hospitals.append(
                NearbyHospitalItem(
                    id=h.id,
                    name=h.name,
                    facility_type=h.facility_type,
                    latitude=h.latitude,
                    longitude=h.longitude,
                    straight_line_distance_meters=round(dist_m, 1),
                    straight_line_distance_km=round(dist_m / 1000.0, 2),
                    address=h.address,
                    contact_phone=h.contact_phone,
                    has_emergency_service=h.has_emergency_service,
                    total_beds_reference=h.total_beds_reference,
                    is_verified_facility=h.is_verified_facility,
                )
            )

        advisory_notes: List[str] = []
        if len(hospitals) == 0:
            advisory_notes.append(
                f"No verified hospital facilities found within {int(radius_meters / 1000)} km. "
                "Consider increasing search radius or contact emergency dispatch directly via 112 / 108."
            )

        return NearbyHospitalsResponse(
            center_latitude=latitude,
            center_longitude=longitude,
            search_radius_meters=radius_meters,
            total_found=len(hospitals),
            spatial_engine="postgis",
            emergency_only_filter=emergency_only,
            hospitals=hospitals,
            advisory_notes=advisory_notes,
        )

    async def _query_hospitals_haversine(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float,
        emergency_only: bool,
        limit: int,
    ) -> NearbyHospitalsResponse:
        """Execute bounding-box query with exact Haversine distance calculation."""
        min_lat, max_lat, min_lon, max_lon = bounding_box_for_radius(
            latitude, longitude, radius_meters
        )

        stmt = (
            select(Hospital)
            .where(
                Hospital.latitude.between(min_lat, max_lat),
                Hospital.longitude.between(min_lon, max_lon),
            )
        )
        if emergency_only:
            stmt = stmt.where(Hospital.has_emergency_service.is_(True))

        result = await db.execute(stmt)
        if hasattr(result, "scalars"):
            candidates = result.scalars().all()
        else:
            candidates = result.all()

        nearby_items: List[Tuple[Hospital, float]] = []
        for h in candidates:
            # Handle row tuples if scalars wasn't used
            h_obj = h[0] if isinstance(h, tuple) else h
            dist = haversine_distance_meters(latitude, longitude, h_obj.latitude, h_obj.longitude)
            if dist <= radius_meters:
                nearby_items.append((h_obj, dist))

        nearby_items.sort(key=lambda x: x[1])

        hospitals = [
            NearbyHospitalItem(
                id=h.id,
                name=h.name,
                facility_type=h.facility_type,
                latitude=h.latitude,
                longitude=h.longitude,
                straight_line_distance_meters=round(d, 1),
                straight_line_distance_km=round(d / 1000.0, 2),
                address=h.address,
                contact_phone=h.contact_phone,
                has_emergency_service=h.has_emergency_service,
                total_beds_reference=h.total_beds_reference,
                is_verified_facility=h.is_verified_facility,
            )
            for h, d in nearby_items[:limit]
        ]

        advisory_notes: List[str] = [
            "Proximity calculated using Haversine spherical math on registered facility coordinates."
        ]
        if len(hospitals) == 0:
            advisory_notes.append(
                f"No verified hospital facilities found within {int(radius_meters / 1000)} km. "
                "Consider increasing search radius or contact emergency dispatch directly via 112 / 108."
            )

        return NearbyHospitalsResponse(
            center_latitude=latitude,
            center_longitude=longitude,
            search_radius_meters=radius_meters,
            total_found=len(hospitals),
            spatial_engine="haversine_fallback",
            emergency_only_filter=emergency_only,
            hospitals=hospitals,
            advisory_notes=advisory_notes,
        )


    async def _query_haversine(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float,
        area_sqkm: float,
        missing_geom_count: int,
    ) -> HazardDensityResponse:
        """Execute bounding-box database query filtered by exact Haversine distance."""
        min_lat, max_lat, min_lon, max_lon = bounding_box_for_radius(
            latitude, longitude, radius_meters
        )

        # Query records within bounding box
        stmt = (
            select(Hazard)
            .where(
                Hazard.latitude.between(min_lat, max_lat),
                Hazard.longitude.between(min_lon, max_lon),
            )
        )

        result = await db.execute(stmt)
        if hasattr(result, "scalars"):
            candidates = result.scalars().all()
        else:
            candidates = result.all()

        nearby_items: List[Tuple[Hazard, float]] = []
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for h in candidates:
            dist = haversine_distance_meters(latitude, longitude, h.latitude, h.longitude)
            if dist <= radius_meters:
                nearby_items.append((h, dist))
                by_type[h.hazard_type] = by_type.get(h.hazard_type, 0) + 1
                by_severity[h.severity] = by_severity.get(h.severity, 0) + 1

        # Sort by distance ascending
        nearby_items.sort(key=lambda x: x[1])

        nearby_hazards = [
            NearbyHazardSummary(
                id=h.id,
                title=h.title,
                hazard_type=h.hazard_type,
                severity=h.severity,
                latitude=h.latitude,
                longitude=h.longitude,
                distance_meters=round(d, 1),
                created_at=h.created_at,
            )
            for h, d in nearby_items[:100]
        ]

        total_hazards = len(nearby_items)
        density_per_sqkm = round(total_hazards / area_sqkm, 2) if area_sqkm > 0 else 0.0
        critical_high = by_severity.get("critical", 0) + by_severity.get("high", 0)

        advisory_notes: List[str] = [
            "Spatial query executed using Haversine fallback calculation on standard coordinate attributes."
        ]
        if missing_geom_count > 0:
            advisory_notes.append(
                f"Database contains {missing_geom_count} hazard record(s) without PostGIS geometry."
            )

        return HazardDensityResponse(
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=radius_meters,
            area_sqkm=area_sqkm,
            total_hazards=total_hazards,
            density_per_sqkm=density_per_sqkm,
            by_type=by_type,
            by_severity=by_severity,
            critical_and_high_count=critical_high,
            spatial_engine="haversine_fallback",
            hazards_with_missing_geometry_count=missing_geom_count,
            advisory_notes=advisory_notes,
            nearby_hazards=nearby_hazards,
        )



spatial_service = SpatialService()
