"""Database session management, async engine configuration, and PostGIS verification."""
import re
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy ORM models
Base = declarative_base()


def sanitize_database_error(msg: Optional[str]) -> Optional[str]:
    """Scrub sensitive credentials, passwords, and tokens from database error strings.

    Prevents credentials in connection strings (e.g. postgresql+asyncpg://user:pass@host)
    from leaking via diagnostics, logs, or API health checks.
    """
    if not msg:
        return msg
    # Mask password portion in database URLs
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(msg))
    return sanitized

# Async SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions to endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connectivity() -> Dict[str, Any]:
    """
    Probe the database and verify PostGIS extension status.
    Accurately reports real connection status without false claims.
    """
    result: Dict[str, Any] = {
        "connected": False,
        "database_url_configured": bool(settings.DATABASE_URL),
        "postgis_enabled": False,
        "postgis_version": None,
        "server_version": None,
        "error": None,
        "setup_guidance": None
    }

    try:
        async with engine.connect() as conn:
            # 1. Test basic connectivity and query server version
            res = await conn.execute(text("SELECT version();"))
            server_version_row = res.fetchone()
            result["connected"] = True
            result["server_version"] = server_version_row[0] if server_version_row else "Unknown"

            # 2. Check for PostGIS extension
            try:
                postgis_res = await conn.execute(text("SELECT PostGIS_Version();"))
                postgis_row = postgis_res.fetchone()
                if postgis_row:
                    result["postgis_enabled"] = True
                    result["postgis_version"] = str(postgis_row[0])
            except Exception as postgis_err:
                logger.warning(f"PostGIS extension check failed: {postgis_err}")
                result["postgis_enabled"] = False
                result["setup_guidance"] = (
                    "PostgreSQL is connected, but PostGIS extension is not installed or enabled in this database. "
                    "Run 'CREATE EXTENSION IF NOT EXISTS postgis;' in PostgreSQL after installing the PostGIS package."
                )

    except Exception as exc:
        error_msg = sanitize_database_error(str(exc))
        logger.error(f"Database connectivity failed: {error_msg}")
        result["connected"] = False
        result["error"] = error_msg
        result["setup_guidance"] = (
            "Cannot connect to PostgreSQL. Please verify: "
            "1. PostgreSQL service is running. "
            "2. Database name, user, and password in backend/.env match your local instance. "
            "3. Target database exists (e.g., 'CREATE DATABASE roadsafety_db;')."
        )

    return result


async def init_db() -> Dict[str, Any]:
    """
    Repeatable database initialization:
    Attempts to enable PostGIS extension and create tables if connected.
    """
    init_status = {"postgis_created": False, "tables_created": False, "error": None}
    try:
        async with engine.begin() as conn:
            # Safely attempt to create postgis extension
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                init_status["postgis_created"] = True
            except Exception as ext_err:
                logger.warning(f"Could not execute 'CREATE EXTENSION postgis': {ext_err}")
                init_status["error"] = f"PostGIS extension notice: {ext_err}"

            # Create all registered tables
            await conn.run_sync(Base.metadata.create_all)
            init_status["tables_created"] = True

    except Exception as exc:
        logger.warning(f"Database initialization could not complete: {exc}")
        init_status["error"] = sanitize_database_error(str(exc))

    return init_status
