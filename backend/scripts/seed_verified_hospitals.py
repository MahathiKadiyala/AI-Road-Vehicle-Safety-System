"""Idempotent reference seeding script for verified hospitals and trauma centers.

Seeds verified public and major referral hospitals in Bengaluru, Karnataka, India
with spatial Point geometries (SRID 4326) and static reference metadata.

Usage:
    # Dry-run inspection (default, non-destructive):
    python backend/scripts/seed_verified_hospitals.py --dry-run

    # Execute seeding with explicit confirmation:
    python backend/scripts/seed_verified_hospitals.py --execute

Safety:
    - Default is --dry-run.
    - Idempotent: checks for facility existence by name before inserting.
    - PostGIS geom populated with ST_SetSRID(ST_MakePoint(lon, lat), 4326).
    - All facility bed counts are static public references, not live telemetry.
"""
import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hospital_seeder")

# Verified reference dataset of major public and trauma hospitals in Bengaluru
VERIFIED_HOSPITALS: List[Dict[str, Any]] = [
    {
        "name": "Victoria Hospital Trauma Care Centre",
        "facility_type": "Trauma Center",
        "latitude": 12.9634,
        "longitude": 77.5746,
        "address": "Fort Road, near City Market, Kalasipalya, Bengaluru 560002",
        "contact_phone": "+91-80-26701150",
        "has_emergency_service": True,
        "total_beds_reference": 200,
        "is_verified_facility": True,
    },
    {
        "name": "Bowring and Lady Curzon Hospital",
        "facility_type": "Super Specialty",
        "latitude": 12.9830,
        "longitude": 77.6046,
        "address": "Lady Curzon Road, Tasker Town, Shivajinagar, Bengaluru 560001",
        "contact_phone": "+91-80-25591325",
        "has_emergency_service": True,
        "total_beds_reference": 686,
        "is_verified_facility": True,
    },
    {
        "name": "NIMHANS Neuro & Trauma Centre",
        "facility_type": "Trauma Center",
        "latitude": 12.9392,
        "longitude": 77.5956,
        "address": "Hosur Road, Lakkasandra, Wilson Garden, Bengaluru 560029",
        "contact_phone": "+91-80-26995000",
        "has_emergency_service": True,
        "total_beds_reference": 1000,
        "is_verified_facility": True,
    },
    {
        "name": "Sri Jayadeva Institute of Cardiovascular Sciences",
        "facility_type": "Super Specialty",
        "latitude": 12.9180,
        "longitude": 77.5975,
        "address": "Bannerghatta Road, Jayanagar 9th Block, Bengaluru 560069",
        "contact_phone": "+91-80-22977200",
        "has_emergency_service": True,
        "total_beds_reference": 1150,
        "is_verified_facility": True,
    },
    {
        "name": "KC General Hospital",
        "facility_type": "General Hospital",
        "latitude": 12.9996,
        "longitude": 77.5710,
        "address": "5th Cross Road, Malleshwaram, Bengaluru 560003",
        "contact_phone": "+91-80-23341771",
        "has_emergency_service": True,
        "total_beds_reference": 500,
        "is_verified_facility": True,
    },
    {
        "name": "St. John's Medical College Hospital",
        "facility_type": "Multi Specialty",
        "latitude": 12.9318,
        "longitude": 77.6200,
        "address": "Sarjapur Road, John Nagar, Koramangala, Bengaluru 560034",
        "contact_phone": "+91-80-22065000",
        "has_emergency_service": True,
        "total_beds_reference": 1350,
        "is_verified_facility": True,
    },
    {
        "name": "Manipal Hospital Old Airport Road",
        "facility_type": "Multi Specialty",
        "latitude": 12.9592,
        "longitude": 77.6475,
        "address": "98, HAL Old Airport Road, Kodihalli, Bengaluru 560017",
        "contact_phone": "+91-80-25024444",
        "has_emergency_service": True,
        "total_beds_reference": 600,
        "is_verified_facility": True,
    },
]


async def seed_hospitals(dry_run: bool = True) -> int:
    """Check and seed verified hospital reference data."""
    logger.info("Connecting to database for hospital seeding...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.connect() as conn:
            # 1. Inspect existing hospitals
            existing_res = await conn.execute(text("SELECT name FROM hospitals;"))
            existing_names = {row[0] for row in existing_res.fetchall()}
            logger.info(f"Existing hospital records in database: {len(existing_names)}")

            to_insert = [h for h in VERIFIED_HOSPITALS if h["name"] not in existing_names]
            logger.info(f"Verified hospital candidates to insert: {len(to_insert)}")

            if not to_insert:
                logger.info("All reference hospital records are already present in database.")
                return 0

            for h in to_insert:
                logger.info(f"  - [{h['facility_type']}] {h['name']} ({h['latitude']}, {h['longitude']})")

            if dry_run:
                logger.info(f"[DRY RUN] Would seed {len(to_insert)} hospital record(s). Run with --execute to commit.")
                return 0

            # 2. Insert records within transaction
            logger.info(f"Inserting {len(to_insert)} hospital records...")
            async with engine.begin() as trans_conn:
                for h in to_insert:
                    h_id = str(uuid.uuid4())
                    insert_stmt = text("""
                        INSERT INTO hospitals (
                            id, name, facility_type, latitude, longitude, geom,
                            address, contact_phone, has_emergency_service,
                            total_beds_reference, is_verified_facility, created_at
                        ) VALUES (
                            :id, :name, :facility_type, :latitude, :longitude,
                            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                            :address, :contact_phone, :has_emergency_service,
                            :total_beds_reference, :is_verified_facility, NOW()
                        );
                    """)
                    await trans_conn.execute(
                        insert_stmt,
                        {
                            "id": h_id,
                            "name": h["name"],
                            "facility_type": h["facility_type"],
                            "latitude": h["latitude"],
                            "longitude": h["longitude"],
                            "address": h["address"],
                            "contact_phone": h["contact_phone"],
                            "has_emergency_service": h["has_emergency_service"],
                            "total_beds_reference": h["total_beds_reference"],
                            "is_verified_facility": h["is_verified_facility"],
                        },
                    )

            logger.info(f"Successfully seeded {len(to_insert)} hospital record(s).")
            return 0

    except Exception as exc:
        logger.error(f"Database operation failed during hospital seeding: {exc}")
        return 1
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Reference hospital seeder for AI Road Safety System.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Inspect existing records and show what would be seeded without modifying the database (default).",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Execute the seed transaction to insert missing reference hospitals.",
    )

    args = parser.parse_args()
    dry_run = not args.execute

    mode_label = "DRY RUN (non-destructive)" if dry_run else "EXECUTE"
    logger.info(f"Starting hospital seeder in {mode_label} mode")

    exit_code = asyncio.run(seed_hospitals(dry_run=dry_run))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
