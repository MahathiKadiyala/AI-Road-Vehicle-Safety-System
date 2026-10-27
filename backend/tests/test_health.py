"""Test suite for health and system diagnostics endpoint."""
from unittest.mock import patch, AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root_health_endpoint():
    """Test that GET /health returns HTTP 200 with complete diagnostics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required top-level fields
        assert "status" in data
        assert "project_name" in data
        assert "version" in data
        assert "environment" in data
        assert "database" in data
        
        # Verify database diagnostics block
        db = data["database"]
        assert isinstance(db["connected"], bool)
        assert isinstance(db["postgis_enabled"], bool)
        assert "database_url_configured" in db


@pytest.mark.asyncio
async def test_api_v1_health_endpoint():
    """Test that GET /api/v1/health returns HTTP 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data


@pytest.mark.asyncio
async def test_health_state_healthy():
    """Test composite health status when DB is connected and PostGIS is enabled."""
    mock_db_info = {
        "connected": True,
        "database_url_configured": True,
        "postgis_enabled": True,
        "postgis_version": "3.6",
        "server_version": "PostgreSQL 17.10",
        "error": None,
        "setup_guidance": None,
    }
    with patch("app.api.v1.endpoints.health.check_database_connectivity", new=AsyncMock(return_value=mock_db_info)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"]["connected"] is True
            assert data["database"]["postgis_enabled"] is True


@pytest.mark.asyncio
async def test_health_state_postgis_pending():
    """Test composite health status when DB is connected but PostGIS is missing."""
    mock_db_info = {
        "connected": True,
        "database_url_configured": True,
        "postgis_enabled": False,
        "postgis_version": None,
        "server_version": "PostgreSQL 17.10",
        "error": None,
        "setup_guidance": "Run CREATE EXTENSION postgis;",
    }
    with patch("app.api.v1.endpoints.health.check_database_connectivity", new=AsyncMock(return_value=mock_db_info)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert "PostGIS extension pending" in data["status"]
            assert data["database"]["connected"] is True
            assert data["database"]["postgis_enabled"] is False


@pytest.mark.asyncio
async def test_health_state_database_unreachable():
    """Test composite health status when DB is disconnected."""
    mock_db_info = {
        "connected": False,
        "database_url_configured": True,
        "postgis_enabled": False,
        "postgis_version": None,
        "server_version": None,
        "error": "Connection refused",
        "setup_guidance": "Check PostgreSQL service",
    }
    with patch("app.api.v1.endpoints.health.check_database_connectivity", new=AsyncMock(return_value=mock_db_info)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert "database unreachable" in data["status"]
            assert data["database"]["connected"] is False
