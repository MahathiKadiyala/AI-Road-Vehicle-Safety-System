-- ==============================================================================
-- Migration: 001_backfill_hazard_geom.sql
-- Project: AI-Powered Road and Vehicle Safety System
-- Purpose: Idempotently backfill missing PostGIS POINT geometries (SRID 4326)
--          from existing validated latitude/longitude coordinates in `hazards`.
--
-- Safety Guarantees:
-- 1. Idempotent: Does NOT touch records where `geom` is already populated.
-- 2. Non-destructive: Preserves original `latitude` and `longitude` fields.
-- 3. Bounds validation: Only populates records with valid WGS84 ranges:
--    - Latitude:  [-90.0, 90.0]
--    - Longitude: [-180.0, 180.0]
-- 4. Spatial ordering: PostGIS WKT POINT(x y) uses x=longitude, y=latitude.
-- ==============================================================================

-- Step 1: Ensure PostGIS extension is available
CREATE EXTENSION IF NOT EXISTS postgis;

-- Step 2: Ensure spatial index exists on hazards.geom
CREATE INDEX IF NOT EXISTS idx_hazards_geom ON hazards USING GIST (geom);

-- Step 3: Backfill missing PostGIS POINT geometry (SRID 4326)
UPDATE hazards
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE geom IS NULL
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude >= -90.0 AND latitude <= 90.0
  AND longitude >= -180.0 AND longitude <= 180.0;

-- Verification check query (returns count of any remaining invalid or null records):
-- SELECT count(*) AS unbackfilled_hazards FROM hazards WHERE geom IS NULL;
