"""Pydantic schemas for application health and diagnostics."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database connectivity and PostGIS status."""
    connected: bool
    database_url_configured: bool
    postgis_enabled: bool
    postgis_version: Optional[str] = None
    server_version: Optional[str] = None
    error: Optional[str] = None
    setup_guidance: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall system health report schema."""
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    project_name: str
    version: str
    environment: str
    database: DatabaseHealth
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
