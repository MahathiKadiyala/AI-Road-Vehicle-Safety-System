"""Phase 9 Security, Reliability, and Error Hardening Regression Test Suite.

Verifies:
1. Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy).
2. CORS configuration security and development origin fallbacks.
3. Database credential and password sanitization in diagnostics.
4. Global unhandled exception handler protection against stack trace/path leaks.
5. Uploaded image security (size limits, content magic byte validation, null byte rejection, UUID filenames, path traversal prevention).
6. Safe deletion containment within upload directory.
7. Model unavailable honesty enforcement (no simulated predictions when weights missing).
8. Statutory parameter validation and mandatory disclaimer enforcement.
"""
import io
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import UploadFile
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.database import sanitize_database_error, check_database_connectivity, get_db
from app.core.storage import (
    validate_and_save_image,
    delete_image_file,
    _validate_image_content,
    _generate_safe_filename,
    ALLOWED_IMAGE_TYPES,
)


# ==============================================================================
# 1. Security Headers & CORS Configuration
# ==============================================================================

@pytest.mark.asyncio
async def test_security_headers_present_on_responses():
    """Verify standard OWASP security headers are present on API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        headers = resp.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_cors_origins_list_security():
    """Verify cors_origins_list defaults safely to explicit origins and trims whitespace."""
    with patch.object(settings, "CORS_ORIGINS", ""):
        assert len(settings.cors_origins_list) >= 2
        assert "http://localhost:5173" in settings.cors_origins_list

    with patch.object(settings, "CORS_ORIGINS", " * "):
        # Wildcard should fall back to safe explicit origins for credentials compatibility
        assert len(settings.cors_origins_list) >= 2
        assert "http://localhost:5173" in settings.cors_origins_list

    with patch.object(settings, "CORS_ORIGINS", "https://app.safety.in , https://admin.safety.in "):
        origins = settings.cors_origins_list
        assert origins == ["https://app.safety.in", "https://admin.safety.in"]


# ==============================================================================
# 2. Database Credential Sanitization
# ==============================================================================

def test_sanitize_database_error_scrubs_passwords():
    """Verify sanitize_database_error scrubs passwords from connection strings."""
    raw_error = "Connection failed to postgresql+asyncpg://admin:super_secret_p%40ss@localhost:5432/roadsafety_db"
    sanitized = sanitize_database_error(raw_error)
    assert sanitized is not None
    assert "super_secret_p%40ss" not in sanitized
    assert "admin:***@" in sanitized

    # Plain text without credentials should be preserved
    plain_error = "FATAL: database 'roadsafety_db' does not exist"
    assert sanitize_database_error(plain_error) == plain_error

    # None input handling
    assert sanitize_database_error(None) is None


@pytest.mark.asyncio
async def test_check_database_connectivity_sanitizes_errors():
    """Verify check_database_connectivity masks any credentials in the diagnostic output."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.side_effect = Exception(
        "asyncpg error: could not connect to postgresql://user:my_secret_password@10.0.0.1:5432/db"
    )
    with patch("sqlalchemy.ext.asyncio.AsyncEngine.connect", return_value=mock_ctx):
        diag = await check_database_connectivity()
        assert diag["connected"] is False
        assert "my_secret_password" not in str(diag["error"])
        assert "user:***@" in str(diag["error"])


# ==============================================================================
# 3. Global Exception Handler Protection Against Leaks
# ==============================================================================

@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_500_without_stacktrace():
    """Verify an unhandled internal exception returns a generic JSON error without path or traceback leaks."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    with patch("app.api.v1.endpoints.health.check_database_connectivity", side_effect=RuntimeError("Secret internal system failure")):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/health")
            assert resp.status_code == 500
            data = resp.json()
            assert "detail" in data
            # Ensure no python file paths or traceback leaked
            assert "Secret internal system failure" not in data["detail"]
            assert "Traceback" not in data["detail"]
            assert ".py" not in data["detail"]
            assert data["detail"] == "An internal server error occurred. Please try again later."


# ==============================================================================
# 4. Image Upload Security & Validation
# ==============================================================================

@pytest.mark.asyncio
async def test_validate_and_save_image_rejects_null_byte_filenames():
    """Verify uploaded filenames containing null bytes or control characters are rejected."""
    upload_mock = MagicMock(spec=UploadFile)
    upload_mock.filename = "image\x00.jpg"
    upload_mock.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0" + b"\x00" * 50)

    with pytest.raises(ValueError, match="control characters or null bytes"):
        await validate_and_save_image(upload_mock)


@pytest.mark.asyncio
async def test_validate_and_save_image_rejects_empty_payload():
    """Verify empty uploaded files are rejected."""
    upload_mock = MagicMock(spec=UploadFile)
    upload_mock.filename = "empty.jpg"
    upload_mock.read = AsyncMock(return_value=b"")

    with pytest.raises(ValueError, match="Uploaded file is empty"):
        await validate_and_save_image(upload_mock)


@pytest.mark.asyncio
async def test_validate_and_save_image_rejects_oversized_payload():
    """Verify uploaded files exceeding MAX_UPLOAD_SIZE_MB are rejected."""
    upload_mock = MagicMock(spec=UploadFile)
    upload_mock.filename = "oversized.jpg"
    oversized = b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024)
    upload_mock.read = AsyncMock(return_value=oversized)

    with pytest.raises(ValueError, match="exceeds the maximum allowed size"):
        await validate_and_save_image(upload_mock)


@pytest.mark.asyncio
async def test_validate_and_save_image_rejects_invalid_magic_bytes():
    """Verify non-image content disguised with a .jpg extension is rejected."""
    upload_mock = MagicMock(spec=UploadFile)
    upload_mock.filename = "fake.jpg"
    upload_mock.read = AsyncMock(return_value=b"<html><script>alert(1)</script></html>")

    with pytest.raises(ValueError, match="Unsupported image format"):
        await validate_and_save_image(upload_mock)


def test_generate_safe_filename_uses_uuid_and_ignores_client_name():
    """Verify generated filename uses pure UUID4 with detected extension."""
    for mime, expected_ext in ALLOWED_IMAGE_TYPES.items():
        fname = _generate_safe_filename(mime)
        assert fname.endswith(expected_ext)
        # Should be UUID4 hex (32 chars) + ext
        stem = Path(fname).stem
        assert len(stem) == 32
        int(stem, 16)  # Must be valid hex


def test_delete_image_file_path_containment():
    """Verify delete_image_file rejects attempts to delete files outside upload dir."""
    # Path traversal attempt
    traversal_path = "../../sensitive_file.txt"
    deleted = delete_image_file(traversal_path)
    assert deleted is False

    # None handling
    assert delete_image_file(None) is False


# ==============================================================================
# 5. Model Unavailability & Zero-Fake-Predictions Invariant
# ==============================================================================

@pytest.mark.asyncio
async def test_risk_prediction_endpoint_unavailable_honesty():
    """Verify risk prediction endpoint returns HTTP 503 when weights are not present."""
    transport = ASGITransport(app=app)
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "road_classification": "urban_arterial",
        "speed_limit_kmh": 50,
        "surface_condition": "dry",
        "lighting_condition": "daylight",
        "weather_condition": "clear",
        "search_radius_meters": 1000,
    }

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/v1/risk/predict", json=payload)
            # Must return 503 Service Unavailable when model is not trained/loaded
            assert resp.status_code == 503
            data = resp.json()
            assert "detail" in data
            assert data["detail"]["error"] == "MODEL_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_vehicle_assessment_mandatory_disclaimer_enforced():
    """Verify vehicle assessment strictly enforces disclaimer acknowledgement."""
    transport = ASGITransport(app=app)
    payload = {
        "make": "Maruti Suzuki",
        "model": "Swift",
        "year": 2020,
        "odometer_km": 40000,
        "vehicle_category": "M1_passenger_car",
        "tyre_tread_depth_mm": 4.0,
        "brake_pad_thickness_mm": 6.0,
        "disclaimer_acknowledged": False,  # Not acknowledged
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/vehicles/assess", json=payload)
        # Should be rejected with 422 Unprocessable Content
        assert resp.status_code == 422
        assert "acknowledgement" in resp.text.lower() or "disclaimer" in resp.text.lower()
