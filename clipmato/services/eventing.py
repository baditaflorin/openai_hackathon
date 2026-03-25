"""Append-only event log, SSE helpers, and webhook delivery."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import hmac
import json
import logging
import os
import threading
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from .. import config as app_config

logger = logging.getLogger(__name__)

EVENT_STREAM_POLL_SECONDS = max(float(os.getenv("CLIPMATO_EVENT_STREAM_POLL_SECONDS", "0.5")), 0.1)
WEBHOOK_POLL_SECONDS = max(float(os.getenv("CLIPMATO_WEBHOOK_POLL_SECONDS", "1.0")), 0.1)
WEBHOOK_MAX_ATTEMPTS = max(int(os.getenv("CLIPMATO_WEBHOOK_MAX_ATTEMPTS", "3")), 1)
WEBHOOK_DELIVERY_TIMEOUT_SECONDS = max(float(os.getenv("CLIPMATO_WEBHOOK_TIMEOUT_SECONDS", "10")), 1.0)


def _events_path() -> Path:
    return app_config.EVENTS_PATH


def _webhooks_path() -> Path:
    return app_config.WEBHOOKS_PATH


def _lock_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.lock")


@contextmanager
def _locked_file(path: Path):
    import fcntl

    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read JSON data from %s", path)
        return copy.deepcopy(default)


def _write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=path.stem + "_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        logger.exception("Failed to write JSON data atomically to %s", path)
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _read_event_lines() -> list[dict[str, Any]]:
    path = _events_path()
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    logger.exception("Ignoring malformed event line")
                    continue
                if isinstance(event, dict):
                    events.append(event)
    except Exception:
        logger.exception("Failed to read event log from %s", path)
    return events


def _next_event_sequence(events: list[dict[str, Any]]) -> int:
    sequence = 0
    for event in reversed(events):
        value = event.get("sequence")
        if isinstance(value, int) and value > sequence:
            sequence = value
            break
    return sequence + 1


def _append_event_line(event: dict[str, Any]) -> None:
    path = _events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")))
        handle.write("\n")


def _read_webhooks() -> list[dict[str, Any]]:
    raw = _read_json_file(_webhooks_path(), [])
    if not isinstance(raw, list):
        return []
    return [copy.deepcopy(item) for item in raw if isinstance(item, dict)]


def _write_webhooks(webhooks: list[dict[str, Any]]) -> None:
    _write_json_file(_webhooks_path(), webhooks)


def _normalize_webhook(raw: dict[str, Any]) -> dict[str, Any]:
    webhook = copy.deepcopy(raw)
    webhook.setdefault("event_types", [])
    webhook.setdefault("enabled", True)
    webhook.setdefault("last_delivered_sequence", 0)
    webhook.setdefault("delivery_attempts", 0)
    webhook.setdefault("last_delivery_at", None)
    webhook.setdefault("last_failed_sequence", None)
    webhook.setdefault("last_failed_event_id", None)
    webhook.setdefault("last_error", None)
    webhook.setdefault("dead_lettered_at", None)
    webhook.setdefault("dead_letter_reason", None)
    return webhook


def _match_filters(
    event: dict[str, Any],
    *,
    record_id: str | None = None,
    run_id: str | None = None,
    publish_job_id: str | None = None,
    event_types: list[str] | None = None,
) -> bool:
    if record_id is not None and event.get("record_id") != record_id and event.get("aggregate_id") != record_id:
        return False
    if run_id is not None and event.get("run_id") != run_id:
        return False
    if publish_job_id is not None and event.get("publish_job_id") != publish_job_id:
        return False
    if event_types and event.get("type") not in event_types:
        return False
    return True


def _resolve_sequence(events: list[dict[str, Any]], event_id: str) -> int | None:
    for event in events:
        if event.get("event_id") == event_id:
            value = event.get("sequence")
            return value if isinstance(value, int) else None
    return None


def _build_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _validate_webhook_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Webhook URL must be an absolute http(s) URL")
    return url


class EventingService:
    """Coordinates event recording, SSE access, and webhook delivery."""

    def __init__(self) -> None:
        self._worker_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    def emit_event(
        self,
        event_type: str,
        *,
        aggregate_id: str | None = None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        record_id: str | None = None,
        run_id: str | None = None,
        publish_job_id: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            record = self._append_event(
                event_type,
                aggregate_id=aggregate_id,
                payload=payload,
                correlation_id=correlation_id,
                record_id=record_id,
                run_id=run_id,
                publish_job_id=publish_job_id,
                source=source,
            )
            return record
        except Exception:
            logger.exception("Failed to append event '%s'", event_type)
            return None

    def _append_event(
        self,
        event_type: str,
        *,
        aggregate_id: str | None = None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        record_id: str | None = None,
        run_id: str | None = None,
        publish_job_id: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        scope_id = aggregate_id or record_id or run_id or publish_job_id
        if scope_id is None:
            raise ValueError("An aggregate_id, record_id, run_id, or publish_job_id is required")

        with _locked_file(_events_path()):
            events = _read_event_lines()
            event = {
                "event_id": uuid4().hex,
                "sequence": _next_event_sequence(events),
                "aggregate_id": scope_id,
                "record_id": record_id,
                "run_id": run_id,
                "publish_job_id": publish_job_id,
                "type": event_type,
                "timestamp": _now_iso(),
                "correlation_id": correlation_id or scope_id,
                "payload": copy.deepcopy(payload or {}),
                "schema_version": 1,
                "source": source,
            }
            _append_event_line(event)
            return copy.deepcopy(event)

    def list_events(
        self,
        *,
        after_sequence: int = 0,
        record_id: str | None = None,
        run_id: str | None = None,
        publish_job_id: str | None = None,
        event_types: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        events = [
            event
            for event in _read_event_lines()
            if isinstance(event.get("sequence"), int)
            and event["sequence"] > after_sequence
            and _match_filters(
                event,
                record_id=record_id,
                run_id=run_id,
                publish_job_id=publish_job_id,
                event_types=event_types,
            )
        ]
        if limit is not None:
            events = events[: max(limit, 0)]
        return copy.deepcopy(events)

    async def stream_events(
        self,
        *,
        after_sequence: int = 0,
        record_id: str | None = None,
        run_id: str | None = None,
        publish_job_id: str | None = None,
        event_types: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        cursor = after_sequence
        while True:
            batch = self.list_events(
                after_sequence=cursor,
                record_id=record_id,
                run_id=run_id,
                publish_job_id=publish_job_id,
                event_types=event_types,
            )
            if batch:
                for event in batch:
                    cursor = int(event["sequence"])
                    yield event
            else:
                await asyncio.sleep(EVENT_STREAM_POLL_SECONDS)

    def register_webhook(
        self,
        *,
        url: str,
        secret: str | None = None,
        event_types: list[str] | None = None,
        record_id: str | None = None,
        run_id: str | None = None,
        publish_job_id: str | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        validated_url = _validate_webhook_url(url)
        webhook = {
            "webhook_id": uuid4().hex,
            "url": validated_url,
            "secret": secret or uuid4().hex,
            "event_types": list(event_types or []),
            "record_id": record_id,
            "run_id": run_id,
            "publish_job_id": publish_job_id,
            "enabled": enabled,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "last_delivered_sequence": 0,
            "last_delivery_at": None,
            "delivery_attempts": 0,
            "last_failed_sequence": None,
            "last_failed_event_id": None,
            "last_error": None,
            "dead_lettered_at": None,
            "dead_letter_reason": None,
        }

        def _mutate(webhooks: list[dict[str, Any]]) -> dict[str, Any]:
            webhooks.append(webhook)
            return copy.deepcopy(webhook)

        return self._mutate_webhooks(_mutate)

    def list_webhooks(self) -> list[dict[str, Any]]:
        return [_normalize_webhook(webhook) for webhook in _read_webhooks()]

    def get_webhook(self, webhook_id: str) -> dict[str, Any] | None:
        for webhook in self.list_webhooks():
            if webhook.get("webhook_id") == webhook_id:
                return webhook
        return None

    def delete_webhook(self, webhook_id: str) -> dict[str, Any] | None:
        def _mutate(webhooks: list[dict[str, Any]]) -> dict[str, Any] | None:
            for index, webhook in enumerate(webhooks):
                if webhook.get("webhook_id") == webhook_id:
                    removed = webhooks.pop(index)
                    return copy.deepcopy(removed)
            return None

        return self._mutate_webhooks(_mutate)

    def replay_webhook(
        self,
        webhook_id: str,
        *,
        from_sequence: int | None = None,
        from_event_id: str | None = None,
    ) -> dict[str, Any]:
        events = _read_event_lines()
        if from_sequence is None and from_event_id is not None:
            from_sequence = _resolve_sequence(events, from_event_id)
        webhook = self.get_webhook(webhook_id)
        if webhook is None:
            raise KeyError(webhook_id)
        if from_sequence is None:
            from_sequence = int(webhook.get("last_failed_sequence") or webhook.get("last_delivered_sequence") or 0) + 1
        replay_cursor = max(int(from_sequence) - 1, 0)

        def _mutate(webhooks: list[dict[str, Any]]) -> dict[str, Any]:
            for stored in webhooks:
                if stored.get("webhook_id") != webhook_id:
                    continue
                stored["last_delivered_sequence"] = replay_cursor
                stored["updated_at"] = _now_iso()
                stored["enabled"] = True
                stored["dead_lettered_at"] = None
                stored["dead_letter_reason"] = None
                stored["last_error"] = None
                stored["last_failed_sequence"] = None
                stored["last_failed_event_id"] = None
                stored["delivery_attempts"] = 0
                return copy.deepcopy(_normalize_webhook(stored))
            raise KeyError(webhook_id)

        updated = self._mutate_webhooks(_mutate)
        return updated

    async def deliver_pending_webhooks_once(self) -> None:
        events = _read_event_lines()
        for webhook in self.list_webhooks():
            if not webhook.get("enabled", True):
                continue
            if webhook.get("dead_lettered_at"):
                continue

            cursor = int(webhook.get("last_delivered_sequence") or 0)
            pending = [
                event
                for event in events
                if isinstance(event.get("sequence"), int)
                and event["sequence"] > cursor
                and _match_filters(
                    event,
                    record_id=webhook.get("record_id"),
                    run_id=webhook.get("run_id"),
                    publish_job_id=webhook.get("publish_job_id"),
                    event_types=list(webhook.get("event_types") or []),
                )
            ]
            for event in pending:
                delivered = await self._deliver_event_with_retries(webhook, event)
                if not delivered:
                    break
                cursor = int(event["sequence"])
                self._update_webhook_delivery_state(
                    webhook["webhook_id"],
                    last_delivered_sequence=cursor,
                    last_delivery_at=_now_iso(),
                    delivery_attempts=0,
                    last_failed_sequence=None,
                    last_failed_event_id=None,
                    last_error=None,
                    dead_lettered_at=None,
                    dead_letter_reason=None,
                )

    async def start_worker(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stop_event = asyncio.Event()
        self._worker_task = asyncio.create_task(self._worker_loop(), name="clipmato-eventing")

    async def stop_worker(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None
        self._stop_event = None

    async def _worker_loop(self) -> None:
        logger.info("Clipmato eventing worker started")
        try:
            if self._stop_event is None:
                return
            while not self._stop_event.is_set():
                try:
                    await self.deliver_pending_webhooks_once()
                except Exception:
                    logger.exception("Eventing worker iteration failed")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=WEBHOOK_POLL_SECONDS)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("Clipmato eventing worker stopped")
            raise

    def _mutate_webhooks(self, mutator):
        with _locked_file(_webhooks_path()):
            webhooks = [_normalize_webhook(webhook) for webhook in _read_webhooks()]
            result = mutator(webhooks)
            _write_webhooks(webhooks)
            return copy.deepcopy(result)

    def _update_webhook_delivery_state(self, webhook_id: str, **updates: Any) -> None:
        def _mutate(webhooks: list[dict[str, Any]]) -> None:
            for webhook in webhooks:
                if webhook.get("webhook_id") == webhook_id:
                    webhook.update(copy.deepcopy(updates))
                    webhook["updated_at"] = _now_iso()
                    return

        self._mutate_webhooks(_mutate)

    async def _deliver_event_with_retries(self, webhook: dict[str, Any], event: dict[str, Any]) -> bool:
        payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
        secret = str(webhook.get("secret") or "")
        last_error: str | None = None
        for attempt in range(1, WEBHOOK_MAX_ATTEMPTS + 1):
            try:
                await asyncio.to_thread(self._send_webhook_request, webhook["url"], payload, secret, event)
                return True
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Webhook delivery failed for %s (attempt %s/%s): %s",
                    webhook.get("webhook_id"),
                    attempt,
                    WEBHOOK_MAX_ATTEMPTS,
                    exc,
                )
                self._update_webhook_delivery_state(
                    webhook["webhook_id"],
                    delivery_attempts=attempt,
                    last_failed_sequence=int(event.get("sequence") or 0),
                    last_failed_event_id=event.get("event_id"),
                    last_error=last_error,
                )
                if attempt < WEBHOOK_MAX_ATTEMPTS:
                    await asyncio.sleep(min(2 ** (attempt - 1), 10))
        self._update_webhook_delivery_state(
            webhook["webhook_id"],
            dead_lettered_at=_now_iso(),
            dead_letter_reason=last_error or "delivery_failed",
        )
        return False

    def _send_webhook_request(
        self,
        url: str,
        payload: bytes,
        secret: str,
        event: dict[str, Any],
    ) -> None:
        headers = {
            "Content-Type": "application/json",
            "X-Clipmato-Event-Id": str(event.get("event_id") or ""),
            "X-Clipmato-Event-Type": str(event.get("type") or ""),
            "X-Clipmato-Event-Sequence": str(event.get("sequence") or ""),
            "X-Clipmato-Signature": _build_signature(payload, secret),
        }
        request = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(request, timeout=WEBHOOK_DELIVERY_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"Unexpected webhook response status: {status}")


eventing_service = EventingService()


def emit_event(
    event_type: str,
    *,
    aggregate_id: str | None = None,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    record_id: str | None = None,
    run_id: str | None = None,
    publish_job_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    return eventing_service.emit_event(
        event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        correlation_id=correlation_id,
        record_id=record_id,
        run_id=run_id,
        publish_job_id=publish_job_id,
        source=source,
    )
