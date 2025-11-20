import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from ..config import (
    ALLOWED_UPLOAD_MIME_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOAD_DIR,
)

# Directory where uploaded files are stored
upload_dir = UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")


def sanitize_filename(filename: str) -> str:
    """Remove path separators and unsafe characters from a filename."""
    normalized = filename.replace("\\", "/")
    name = Path(normalized).name
    sanitized = _SAFE_FILENAME_PATTERN.sub("_", name)
    return sanitized or "upload"


def generate_unique_filename(filename: str) -> str:
    """Return a sanitized filename suffixed with a UUID to prevent collisions."""
    sanitized = sanitize_filename(filename)
    base = Path(sanitized).stem or "upload"
    suffix = Path(sanitized).suffix
    return f"{base}_{uuid4().hex}{suffix}"


def _validate_content_type(upload_file: UploadFile) -> None:
    """Ensure the uploaded file's MIME type is permitted."""
    if upload_file.content_type not in ALLOWED_UPLOAD_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_MIME_TYPES))
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type. Allowed types: {allowed}",
        )


def _copy_file_with_limit(upload_file: UploadFile, destination: Path) -> int:
    """Copy an UploadFile to destination while enforcing the maximum size."""
    total = 0
    try:
        with open(destination, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum size is"
                        f" {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
                    )
                buffer.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    return total


def save_upload_file(upload_file: UploadFile) -> str:
    """
    Save an uploaded FastAPI UploadFile to the uploads directory
    after validating its MIME type and size, using a unique filename,
    and return its file path.
    """
    _validate_content_type(upload_file)
    upload_file.file.seek(0)
    dest = upload_dir / generate_unique_filename(upload_file.filename)
    _copy_file_with_limit(upload_file, dest)
    return str(dest)
