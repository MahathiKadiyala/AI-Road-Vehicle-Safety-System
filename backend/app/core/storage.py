"""Modular image storage service for hazard report uploads.

Validates image content (not just filenames), generates safe unique filenames,
enforces size limits, and prevents path traversal. Designed so the storage
backend can be swapped to S3/GCS later by implementing the same interface.
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowed MIME types and their canonical extensions
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Magic-byte signatures for content-based validation
IMAGE_MAGIC_BYTES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # RIFF header; full check includes "WEBP" at offset 8
}


def _validate_image_content(header: bytes) -> Optional[str]:
    """Detect actual image type by inspecting file header bytes.

    Returns the MIME type if valid, or None if unrecognized.
    """
    for mime_type, signatures in IMAGE_MAGIC_BYTES.items():
        for sig in signatures:
            if header.startswith(sig):
                # Extra check for WEBP: bytes 8-12 must be "WEBP"
                if mime_type == "image/webp" and len(header) >= 12:
                    if header[8:12] != b"WEBP":
                        continue
                return mime_type
    return None


def _generate_safe_filename(detected_mime: str) -> str:
    """Generate a unique, safe filename using UUID4 and the correct extension."""
    ext = ALLOWED_IMAGE_TYPES.get(detected_mime, ".bin")
    return f"{uuid.uuid4().hex}{ext}"


async def validate_and_save_image(file: UploadFile) -> Tuple[str, str]:
    """Validate and save an uploaded image file.

    Returns:
        Tuple of (relative_path, absolute_path) on success.

    Raises:
        ValueError: If the file fails validation (wrong type, too large, etc.).
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # 1. Read the file content (enforcing size limit)
    content = await file.read()
    if len(content) == 0:
        raise ValueError("Uploaded file is empty.")
    if len(content) > max_bytes:
        raise ValueError(
            f"File size ({len(content) / (1024*1024):.1f} MB) exceeds "
            f"the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # 2. Validate content by inspecting magic bytes (not trusting filename/Content-Type)
    header = content[:16]  # Read enough bytes for all checks
    detected_mime = _validate_image_content(header)
    if detected_mime is None:
        raise ValueError(
            f"Unsupported image format. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}. "
            "The file content did not match any recognized image format."
        )

    # 3. Generate safe server-side filename (never trust client filenames)
    safe_filename = _generate_safe_filename(detected_mime)

    # 4. Resolve absolute path and prevent path traversal
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = (upload_dir / safe_filename).resolve()
    # Ensure the destination is actually within the upload directory
    if not str(dest_path).startswith(str(upload_dir)):
        raise ValueError("Invalid filename: path traversal detected.")

    # 5. Write file to disk
    with open(dest_path, "wb") as f:
        f.write(content)

    # Store relative path in database (portable across environments)
    relative_path = f"uploads/{safe_filename}"

    logger.info(
        f"Image saved: {relative_path} ({detected_mime}, {len(content)} bytes)"
    )

    return relative_path, str(dest_path)


def get_image_url(relative_path: Optional[str]) -> Optional[str]:
    """Convert a stored relative path to a URL path for the frontend.

    Returns None if no image is stored.
    """
    if not relative_path:
        return None
    # The static mount in main.py serves /static/uploads/...
    # relative_path is stored as "uploads/<filename>"
    return f"/static/{relative_path}"


def delete_image_file(file_identifier: Optional[str]) -> bool:
    """Delete an uploaded image file if database persistence fails.

    Accepts an absolute path or relative path (e.g. 'uploads/uuid.jpg').
    Guards against path traversal and logs deletion.
    """
    if not file_identifier:
        return False
    try:
        raw_path = Path(file_identifier)
        upload_dir = Path(settings.UPLOAD_DIR).resolve()

        if raw_path.is_absolute():
            target_path = raw_path.resolve()
        else:
            # Strip any leading 'uploads/' if present to locate in upload_dir
            target_path = (upload_dir / raw_path.name).resolve()

        # Strict containment check to prevent deleting arbitrary files
        if not str(target_path).startswith(str(upload_dir)):
            logger.warning(f"Refusing to delete path outside upload directory: {target_path}")
            return False

        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            logger.info(f"Cleaned up orphaned image file: {target_path.name}")
            return True
    except Exception as err:
        logger.warning(f"Failed to cleanup image file {file_identifier}: {err}")
    return False
