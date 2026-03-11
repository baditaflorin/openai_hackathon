"""Static asset hashing and cache helpers."""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from ..config import STATIC_BUILD_DIR, STATIC_DIR

_manifest: dict[str, str] = {}


def _hashed_name(path: Path, digest: str) -> str:
    suffix = "".join(path.suffixes)
    stem = path.name[: -len(suffix)] if suffix else path.name
    return f"{stem}.{digest[:8]}{suffix}"


def build_static_assets() -> dict[str, str]:
    """Copy source assets into the build dir under content-hashed names."""
    global _manifest
    manifest: dict[str, str] = {}
    for source in sorted(path for path in STATIC_DIR.rglob("*") if path.is_file()):
        rel = source.relative_to(STATIC_DIR)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        hashed_rel = rel.with_name(_hashed_name(rel, digest))
        target = STATIC_BUILD_DIR / hashed_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or source.read_bytes() != target.read_bytes():
            shutil.copy2(source, target)
        manifest[rel.as_posix()] = hashed_rel.as_posix()
    _manifest = manifest
    return dict(_manifest)


def static_asset_path(path: str) -> str:
    """Return the hashed URL path for a logical asset."""
    normalized = str(path).lstrip("/")
    hashed = _manifest.get(normalized, normalized)
    return f"/static/{hashed}"


class CachedStaticFiles(StaticFiles):
    """StaticFiles with long-lived cache headers for hashed asset names."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code >= 400:
            return response
        filename = os.path.basename(path)
        if len(filename.split(".")) >= 3:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=300"
        return response
