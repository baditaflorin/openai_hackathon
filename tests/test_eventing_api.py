import asyncio
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from clipmato import config
from clipmato.routers.events import router as events_router
from clipmato.services import eventing
from clipmato.utils import file_io, progress


@pytest.fixture(autouse=True)
def isolated_event_store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path, raising=False)
    monkeypatch.setattr(config, "EVENTS_PATH", tmp_path / "events.jsonl", raising=False)
    monkeypatch.setattr(config, "WEBHOOKS_PATH", tmp_path / "webhooks.json", raising=False)
    monkeypatch.setattr(file_io, "upload_dir", tmp_path, raising=False)
    monkeypatch.setattr(progress, "upload_dir", tmp_path, raising=False)
    eventing.eventing_service._worker_task = None
    eventing.eventing_service._stop_event = None
    return tmp_path


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(events_router)
    return app


def _read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_progress_updates_append_events(isolated_event_store):
    progress.update_progress("record-1", "transcribing", "warming up")
    progress.update_progress("record-1", "complete")

    events = _read_events(isolated_event_store / "events.jsonl")

    assert [event["sequence"] for event in events] == [1, 2]
    assert [event["type"] for event in events] == [
        "record.progress.updated",
        "record.progress.updated",
    ]
    assert events[0]["payload"]["stage"] == "transcribing"
    assert events[0]["payload"]["message"] == "warming up"
    assert events[1]["payload"]["stage"] == "complete"


def test_sse_stream_replays_backfilled_events(isolated_event_store):
    app = _build_app()
    client = TestClient(app)

    eventing.emit_event(
        "record.uploaded",
        aggregate_id="record-2",
        record_id="record-2",
        payload={"filename": "clip.wav"},
        correlation_id="record-2",
        source="upload",
    )

    with client.stream("GET", "/api/v1/events/stream?record_id=record-2&limit=1") as response:
        lines: list[str] = []
        for line in response.iter_lines():
            if not line:
                break
            lines.append(line)

    assert any("record.uploaded" in line for line in lines)
    assert any('"record_id":"record-2"' in line for line in lines)


def test_webhook_delivery_dead_letters_and_replays(isolated_event_store, monkeypatch):
    app = _build_app()
    client = TestClient(app)

    async def noop_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(eventing.asyncio, "sleep", noop_sleep)

    deliveries: list[dict] = []
    delivery_mode = {"fail": True}

    class DummyResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        headers = {key.lower(): value for key, value in request.header_items()}
        deliveries.append(
            {
                "url": request.full_url,
                "headers": headers,
                "body": request.data.decode("utf-8"),
                "timeout": timeout,
            }
        )
        if delivery_mode["fail"]:
            raise eventing.URLError("boom")
        return DummyResponse()

    monkeypatch.setattr(eventing, "urlopen", fake_urlopen)

    webhook_response = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.test/hooks",
            "secret": "shared-secret",
            "event_types": ["record.processing.completed"],
            "record_id": "record-3",
        },
    )
    assert webhook_response.status_code == 201
    webhook = webhook_response.json()

    event = eventing.emit_event(
        "record.processing.completed",
        aggregate_id="record-3",
        record_id="record-3",
        payload={"result": "ok"},
        correlation_id="record-3",
        source="file_processing",
    )
    assert event is not None

    asyncio.run(eventing.eventing_service.deliver_pending_webhooks_once())

    stored = eventing.eventing_service.get_webhook(webhook["webhook_id"])
    assert stored is not None
    assert stored["dead_lettered_at"] is not None
    assert stored["delivery_attempts"] == 3
    assert len(deliveries) == 3
    assert deliveries[0]["headers"]["x-clipmato-signature"].startswith("sha256=")
    assert json.loads(deliveries[0]["body"])["type"] == "record.processing.completed"

    delivery_mode["fail"] = False
    replay_response = client.post(
        f"/api/v1/webhooks/{webhook['webhook_id']}/replay",
        json={"from_sequence": event["sequence"]},
    )
    assert replay_response.status_code == 200

    asyncio.run(eventing.eventing_service.deliver_pending_webhooks_once())

    replayed = eventing.eventing_service.get_webhook(webhook["webhook_id"])
    assert replayed is not None
    assert replayed["dead_lettered_at"] is None
    assert replayed["last_delivered_sequence"] == event["sequence"]
    assert len(deliveries) == 4
