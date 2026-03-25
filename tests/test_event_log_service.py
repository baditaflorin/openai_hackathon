from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from queue import Empty

from clipmato.services.event_log import EventEnvelope, EventLogService


class EventLogServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.log_path = Path(self.tempdir.name) / "event_log.jsonl"

    def new_service(self) -> EventLogService:
        return EventLogService(path=self.log_path)

    def test_append_and_replay_persists_events(self) -> None:
        service = self.new_service()

        appended = EventEnvelope(
            event_id="event-1",
            aggregate_id="record-123",
            type="audit.action",
            timestamp="2026-03-25T10:00:00+00:00",
            payload={
                "action": "publish_requested",
                "outcome": "recorded",
                "details": {"source": "api"},
            },
            correlation_id="corr-1",
            scopes=("record:write",),
            tags=("audit", "api"),
        )
        service.append(appended)

        replayed = self.new_service().replay()

        self.assertEqual(len(replayed), 1)
        event = replayed[0]
        self.assertEqual(event.event_id, appended.event_id)
        self.assertEqual(event.aggregate_id, "record-123")
        self.assertEqual(event.type, "audit.action")
        self.assertEqual(event.correlation_id, "corr-1")
        self.assertEqual(event.payload["action"], "publish_requested")
        self.assertEqual(event.payload["outcome"], "recorded")
        self.assertEqual(event.payload["details"], {"source": "api"})
        self.assertEqual(event.scopes, ("record:write",))
        self.assertEqual(event.tags, ("audit", "api"))
        self.assertTrue(event.timestamp)

    def test_read_events_filters_by_aggregate_and_type(self) -> None:
        service = self.new_service()
        first = service.append_event(
            aggregate_id="record-123",
            type="record.created",
            payload={"step": 1},
        )
        second = service.emit_audit(
            aggregate_id="record-123",
            action="publish",
            outcome="succeeded",
            payload={"remote_id": "vid-1"},
        )
        service.emit(
            aggregate_id="record-999",
            type="record.created",
            payload={"step": 2},
        )

        by_aggregate = service.replay(aggregate_id="record-123")
        by_type = service.replay(event_type="record.created")
        limited = service.replay(limit=1)

        self.assertEqual(len(by_aggregate), 2)
        self.assertEqual([event.event_id for event in by_aggregate], [first.event_id, second.event_id])
        self.assertEqual([event.aggregate_id for event in by_aggregate], ["record-123", "record-123"])
        self.assertEqual([event.aggregate_id for event in by_type], ["record-123", "record-999"])
        self.assertEqual([event.type for event in by_type], ["record.created", "record.created"])
        self.assertEqual([event.event_id for event in limited], [first.event_id])

    def test_read_events_since_event_id_skips_cursor_event(self) -> None:
        service = self.new_service()
        first = service.emit(aggregate_id="record-1", type="step.one", payload={"n": 1})
        second = service.emit(aggregate_id="record-1", type="step.two", payload={"n": 2})
        third = service.emit(aggregate_id="record-1", type="step.three", payload={"n": 3})

        after_first = service.replay(since_event_id=first.event_id)
        after_second = service.replay(since_event_id=second.event_id)

        self.assertEqual([event.event_id for event in after_first], [second.event_id, third.event_id])
        self.assertEqual([event.event_id for event in after_second], [third.event_id])

    def test_live_subscription_receives_appended_events(self) -> None:
        service = self.new_service()
        subscription = service.subscribe(buffer_size=1)
        self.addCleanup(subscription.close)

        appended = service.emit(
            aggregate_id="record-live",
            type="record.live",
            payload={"state": "ready"},
            correlation_id="corr-live",
            scopes=["stream:read"],
            tags=["sse"],
        )

        try:
            received = subscription.queue.get(timeout=1.0)
        except Empty as exc:  # pragma: no cover
            self.fail(f"subscription did not receive appended event: {exc}")

        self.assertEqual(received.event_id, appended.event_id)
        self.assertEqual(received.aggregate_id, "record-live")
        self.assertEqual(received.type, "record.live")
        self.assertEqual(received.payload, {"state": "ready"})
        self.assertEqual(received.correlation_id, "corr-live")
        self.assertEqual(received.scopes, ("stream:read",))
        self.assertEqual(received.tags, ("sse",))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
