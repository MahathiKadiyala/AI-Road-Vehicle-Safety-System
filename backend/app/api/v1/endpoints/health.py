"""Health and system diagnostics endpoint."""
from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_database_connectivity
from app.schemas.health import HealthResponse, DatabaseHealth

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="System Health & PostGIS Status")
async def get_health_status() -> HealthResponse:
    """
    Returns system status, active version, database connectivity,
    and PostGIS extension verification.
    """
    db_info = await check_database_connectivity()

    # Determine composite health status
    if db_info["connected"] and db_info["postgis_enabled"]:
        status = "healthy"
    elif db_info["connected"]:
        status = "degraded (database connected, PostGIS extension pending)"
    else:
        status = "degraded (database unreachable)"

    return HealthResponse(
        status=status,
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(
            connected=db_info["connected"],
            database_url_configured=db_info["database_url_configured"],
            postgis_enabled=db_info["postgis_enabled"],
            postgis_version=db_info["postgis_version"],
            server_version=db_info["server_version"],
            error=db_info["error"],
            setup_guidance=db_info["setup_guidance"]
        )
    )
