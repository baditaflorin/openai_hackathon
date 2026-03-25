"""Append-only event log with JSONL persistence and in-process subscriptions."""
from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4

try:  # pragma: no cover - POSIX is exercised in tests, Windows fallback is defensive.
    import fcntl  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from ..config import EVENT_LOG_PATH


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """A durable audit/event envelope suitable for replay and streaming."""

    event_id: str
    aggregate_id: str
    type: str
    timestamp: str
    payload: dict[str, Any]
    correlation_id: str | None = None
    scopes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the envelope into a JSON-compatible dictionary."""
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": copy.deepcopy(self.payload),
            "correlation_id": self.correlation_id,
            "scopes": list(self.scopes),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        """Build an envelope from a JSON-decoded dictionary."""
        return cls(
            event_id=str(data["event_id"]),
            aggregate_id=str(data.get("aggregate_id") or ""),
            type=str(data["type"]),
            timestamp=str(data["timestamp"]),
            payload=copy.deepcopy(dict(data.get("payload") or {})),
            correlation_id=data.get("correlation_id"),
            scopes=tuple(str(item) for item in data.get("scopes") or ()),
            tags=tuple(str(item) for item in data.get("tags") or ()),
        )


@dataclass(slots=True)
class EventSubscription:
    """A live subscription backed by a thread-safe queue."""

    queue: Queue[EventEnvelope]
    _service: "EventLogService"
    _subscriber_id: int
    closed: bool = False

    def close(self) -> None:
        """Unregister the subscription and stop future fanout."""
        if self.closed:
            return
        self._service._unsubscribe(self._subscriber_id)
        self.closed = True


@dataclass(slots=True)
class _Subscriber:
    queue: Queue[EventEnvelope]
    aggregate_id: str | None
    event_type: str | None


@contextmanager
def _locked_handle(path: Path, mode: str, *, exclusive: bool) -> Iterator[Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open(mode, encoding="utf-8")
    try:
        _lock_file(handle, exclusive=exclusive)
        yield handle
    finally:
        _unlock_file(handle)
        handle.close()


def _lock_file(handle: Any, *, exclusive: bool) -> None:
    if fcntl is None:  # pragma: no cover - defensive fallback
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)


def _unlock_file(handle: Any) -> None:
    if fcntl is None:  # pragma: no cover - defensive fallback
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _normalize_optional_strings(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(str(value) for value in values)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EventLogService:
    """Append-only event log with replay and live fanout."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else EVENT_LOG_PATH
        self._state_lock = RLock()
        self._subscribers: dict[int, _Subscriber] = {}
        self._next_subscriber_id = 1

    def append(
        self,
        event: EventEnvelope | dict[str, Any],
    ) -> EventEnvelope:
        """Append a pre-built event envelope or a JSON-decoded event mapping."""
        envelope = self._coerce_envelope(event)
        self._append_envelope(envelope)
        return envelope

    def emit(
        self,
        *,
        type: str,
        payload: dict[str, Any] | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        timestamp: str | None = None,
        event_id: str | None = None,
    ) -> EventEnvelope:
        """Create and append a new event."""
        envelope = EventEnvelope(
            event_id=event_id or uuid4().hex,
            aggregate_id=str(aggregate_id or ""),
            type=str(type),
            timestamp=timestamp or _utc_now_iso(),
            payload=copy.deepcopy(payload or {}),
            correlation_id=correlation_id,
            scopes=_normalize_optional_strings(scopes),
            tags=_normalize_optional_strings(tags),
        )
        return self.append(envelope)

    def replay(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        since_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[EventEnvelope]:
        """Replay events with optional aggregate, type, cursor, and limit filters."""
        events = self._load_events()
        if since_event_id is not None:
            events = self._slice_after_event(events, since_event_id)
        if aggregate_id is not None:
            events = [event for event in events if event.aggregate_id == aggregate_id]
        if event_type is not None:
            events = [event for event in events if event.type == event_type]
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be greater than or equal to zero")
            events = events[:limit]
        return [self._clone_event(event) for event in events]

    def subscribe(self, buffer_size: int = 10) -> EventSubscription:
        """Register a live subscriber queue for future matching events."""
        queue: Queue[EventEnvelope] = Queue(maxsize=max(buffer_size, 0))
        with self._state_lock:
            subscriber_id = self._next_subscriber_id
            self._next_subscriber_id += 1
            self._subscribers[subscriber_id] = _Subscriber(queue=queue, aggregate_id=None, event_type=None)
        return EventSubscription(queue=queue, _service=self, _subscriber_id=subscriber_id)

    def emit_audit(
        self,
        *,
        aggregate_id: str,
        action: str,
        outcome: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        timestamp: str | None = None,
    ) -> EventEnvelope:
        """Append a convenience audit/outcome event for API and MCP integration."""
        return self.emit(
            aggregate_id=aggregate_id,
            type="audit.action",
            payload={
                "action": action,
                "outcome": outcome,
                "details": copy.deepcopy(payload or {}),
            },
            correlation_id=correlation_id,
            scopes=scopes,
            tags=tags,
            timestamp=timestamp,
        )

    def append_event(
        self,
        *,
        aggregate_id: str,
        type: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        timestamp: str | None = None,
        event_id: str | None = None,
    ) -> EventEnvelope:
        """Compatibility wrapper for older call sites."""
        return self.emit(
            aggregate_id=aggregate_id,
            type=type,
            payload=payload,
            correlation_id=correlation_id,
            scopes=scopes,
            tags=tags,
            timestamp=timestamp,
            event_id=event_id,
        )

    def append_audit_event(
        self,
        *,
        aggregate_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        timestamp: str | None = None,
    ) -> EventEnvelope:
        """Compatibility wrapper for the older audit helper."""
        return self.emit_audit(
            aggregate_id=aggregate_id,
            action=action,
            outcome="recorded",
            payload=payload,
            correlation_id=correlation_id,
            scopes=scopes,
            tags=tags,
            timestamp=timestamp,
        )

    def append_action_outcome_event(
        self,
        *,
        aggregate_id: str,
        action: str,
        outcome: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        scopes: list[str] | tuple[str, ...] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        timestamp: str | None = None,
    ) -> EventEnvelope:
        """Compatibility wrapper for the older action outcome helper."""
        return self.emit_audit(
            aggregate_id=aggregate_id,
            action=action,
            outcome=outcome,
            payload=payload,
            correlation_id=correlation_id,
            scopes=scopes,
            tags=tags,
            timestamp=timestamp,
        )

    def read_events(
        self,
        *,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        since_event_id: str | None = None,
    ) -> list[EventEnvelope]:
        """Compatibility wrapper for replay."""
        return self.replay(
            aggregate_id=aggregate_id,
            event_type=event_type,
            since_event_id=since_event_id,
        )

    def _append_envelope(self, envelope: EventEnvelope) -> None:
        self._write_envelope(envelope)
        self._fanout(envelope)

    def _coerce_envelope(self, event: EventEnvelope | dict[str, Any]) -> EventEnvelope:
        if isinstance(event, EventEnvelope):
            return self._clone_event(event)
        if isinstance(event, dict):
            return EventEnvelope.from_dict(event)
        raise TypeError("event must be an EventEnvelope or event mapping")

    def _write_envelope(self, envelope: EventEnvelope) -> None:
        entry = envelope.to_dict()
        line = json.dumps(entry, separators=(",", ":"))
        with _locked_handle(self.path, "a", exclusive=True) as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _fanout(self, envelope: EventEnvelope) -> None:
        with self._state_lock:
            subscribers = list(self._subscribers.values())
        for subscriber in subscribers:
            if subscriber.aggregate_id is not None and subscriber.aggregate_id != envelope.aggregate_id:
                continue
            if subscriber.event_type is not None and subscriber.event_type != envelope.type:
                continue
            subscriber.queue.put(self._clone_event(envelope))

    def _unsubscribe(self, subscriber_id: int) -> None:
        with self._state_lock:
            self._subscribers.pop(subscriber_id, None)

    def _load_events(self) -> list[EventEnvelope]:
        if not self.path.exists():
            return []
        with _locked_handle(self.path, "r", exclusive=False) as handle:
            raw_lines = handle.read().splitlines()
        events: list[EventEnvelope] = []
        for raw_line in raw_lines:
            if not raw_line.strip():
                continue
            events.append(EventEnvelope.from_dict(json.loads(raw_line)))
        return events

    @staticmethod
    def _slice_after_event(events: list[EventEnvelope], since_event_id: str) -> list[EventEnvelope]:
        for index, event in enumerate(events):
            if event.event_id == since_event_id:
                return events[index + 1 :]
        raise KeyError(since_event_id)

    @staticmethod
    def _clone_event(event: EventEnvelope) -> EventEnvelope:
        return EventEnvelope(
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            type=event.type,
            timestamp=event.timestamp,
            payload=copy.deepcopy(event.payload),
            correlation_id=event.correlation_id,
            scopes=tuple(event.scopes),
            tags=tuple(event.tags),
        )
