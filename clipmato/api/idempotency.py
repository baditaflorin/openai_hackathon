"""In-process idempotency helpers for public API mutations."""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import UploadFile


def _stable_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def fingerprint_payload(payload: dict[str, Any]) -> str:
    """Return a stable fingerprint for a JSON-compatible payload."""
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def fingerprint_upload(upload_file: UploadFile, payload: dict[str, Any]) -> str:
    """Return a stable fingerprint for a multipart upload request."""
    digest = hashlib.sha256()
    digest.update(_stable_json_bytes(payload))
    digest.update((upload_file.filename or "").encode("utf-8"))
    digest.update((upload_file.content_type or "").encode("utf-8"))

    upload_file.file.seek(0)
    while True:
        chunk = upload_file.file.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    upload_file.file.seek(0)
    return digest.hexdigest()


@dataclass(slots=True)
class StoredResponse:
    fingerprint: str
    status_code: int
    body: dict[str, Any]


class IdempotencyStore:
    """Thread-safe in-memory idempotency response cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._responses: dict[str, StoredResponse] = {}

    def lookup(self, scope_key: str, fingerprint: str) -> StoredResponse | None:
        """Return a cached response or raise when the key is reused for a new payload."""
        with self._lock:
            stored = self._responses.get(scope_key)
            if stored is None:
                return None
            if stored.fingerprint != fingerprint:
                raise ValueError("Idempotency key was already used for a different request payload.")
            return stored

    def store_response(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        status_code: int,
        body: dict[str, Any],
    ) -> None:
        """Cache a completed mutation response for future retries."""
        with self._lock:
            self._responses[scope_key] = StoredResponse(
                fingerprint=fingerprint,
                status_code=status_code,
                body=dict(body),
            )

    def clear(self) -> None:
        """Clear the stored idempotency responses."""
        with self._lock:
            self._responses.clear()


idempotency_store = IdempotencyStore()
