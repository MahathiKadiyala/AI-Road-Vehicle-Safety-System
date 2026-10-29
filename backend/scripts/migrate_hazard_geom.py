"""Idempotent database migration script for backfilling PostGIS hazard geometry.

Usage:
    # Dry-run inspection (default, non-destructive):
    python backend/scripts/migrate_hazard_geom.py --dry-run

    # Execute backfill with explicit confirmation:
    python backend/scripts/migrate_hazard_geom.py --execute

Safety:
    - Never modifies existing latitude or longitude values.
    - Only updates records where geom is NULL and coordinates are valid.
    - Idempotent: running multiple times produces identical results.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path if executed standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hazard_migration")


async def run_migration(dry_run: bool = True) -> int:
    """Run geometry backfill migration or dry-run assessment."""
    logger.info("Connecting to database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.connect() as conn:
            # 1. Check PostGIS extension
            try:
                res = await conn.execute(text("SELECT PostGIS_Version();"))
                row = res.fetchone()
                postgis_version = str(row[0]) if row else "Unknown"
                logger.info(f"PostGIS extension detected: {postgis_version}")
            except Exception as e:
                logger.error(f"PostGIS check failed: {e}. PostGIS extension is required.")
                return 1

            # 2. Count records needing backfill
            count_res = await conn.execute(
                text("SELECT count(*) FROM hazards WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL;")
            )
            count_row = count_res.fetchone()
            pending_count = count_row[0] if count_row else 0
            logger.info(f"Records needing geometry backfill: {pending_count}")

            if pending_count == 0:
                logger.info("All hazard records already have valid PostGIS geometry. No action needed.")
                return 0

            if dry_run:
                logger.info(f"[DRY RUN] Would update {pending_count} record(s). Run with --execute to apply.")
                return 0

            # 3. Apply backfill in transaction
            logger.info(f"Applying backfill to {pending_count} record(s)...")
            async with engine.begin() as trans_conn:
                # Ensure spatial index exists
                await trans_conn.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_hazards_geom ON hazards USING GIST (geom);")
                )

                update_res = await trans_conn.execute(
                    text("""
                        UPDATE hazards
                        SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                        WHERE geom IS NULL
                          AND latitude IS NOT NULL
                          AND longitude IS NOT NULL
                          AND latitude BETWEEN -90.0 AND 90.0
                          AND longitude BETWEEN -180.0 AND 180.0;
                    """)
                )
                rows_updated = update_res.rowcount
                logger.info(f"Successfully backfilled geometry for {rows_updated} record(s).")
                return 0

    except Exception as exc:
        logger.error(f"Migration error: {exc}")
        return 1
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Backfill missing PostGIS POINT geometries.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview pending updates without modifying data.")
    parser.add_argument("--execute", action="store_true", help="Execute the backfill migration.")
    args = parser.parse_args()

    execute_mode = args.execute
    dry_run = not execute_mode

    status_code = asyncio.run(run_migration(dry_run=dry_run))
    sys.exit(status_code)


if __name__ == "__main__":
    main()
