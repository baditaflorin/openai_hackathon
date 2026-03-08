"""Shared publishing provider primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class PublishResult:
    """Normalized publish result returned by provider adapters."""

    remote_id: str
    remote_url: str
    published_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, object] = field(default_factory=dict)


class PublishError(RuntimeError):
    """Base exception for publish failures."""

    retryable = False
    blocked = False


class PublishTemporaryError(PublishError):
    """Failure that should be retried automatically."""

    retryable = True


class PublishConfigurationError(PublishError):
    """Failure caused by missing app configuration or unsupported input."""

    blocked = True


class PublishAuthorizationError(PublishError):
    """Failure caused by missing or revoked third-party authorization."""

    blocked = True
