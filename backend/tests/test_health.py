"""Test suite for health and system diagnostics endpoint."""
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
