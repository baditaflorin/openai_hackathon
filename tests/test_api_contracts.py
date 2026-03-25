from __future__ import annotations

import json
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clipmato import __version__
from clipmato import web as web_module
from clipmato.api.idempotency import idempotency_store
from clipmato.routers import public_api as public_api_module
from clipmato.dependencies import (
    get_file_io_service,
    get_processing_service,
    get_progress_service,
    get_project_preset_service,
)


@dataclass
class DummyFileIOService:
    return_path: str
    saved_filenames: list[str] = field(default_factory=list)

    def save(self, upload_file):
        self.saved_filenames.append(upload_file.filename or "")
        return self.return_path


class DummyProcessingService:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def process(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyProgressService:
    def __init__(self) -> None:
        self.updates: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def update(self, *args, **kwargs):
        self.updates.append((args, kwargs))

    def read(self, record_id):
        return {"stage": "pending", "progress": 0, "record_id": record_id}

    def enrich(self, records):
        return records


class DummyProjectPresetService:
    def merge_context(self, preset_ids, manual_context):
        return manual_context

    def read(self):
        return []


class DummyLifecyclePublishingService:
    async def start_worker(self):
        return None

    async def stop_worker(self):
        return None


@pytest.fixture()
def api_app(monkeypatch):
    monkeypatch.setattr(web_module, "build_static_assets", lambda: None)
    monkeypatch.setattr(web_module.metadata_cache, "warm", lambda: None)
    monkeypatch.setattr(web_module, "get_publishing_service", lambda: DummyLifecyclePublishingService())
    monkeypatch.setattr(
        public_api_module,
        "get_runtime_status",
        lambda: {
            "blockers": [],
            "transcription_backend": "openai",
            "local_whisper_device": "cpu",
        },
    )

    idempotency_store.clear()
    web_module.app.dependency_overrides.clear()
    yield web_module.app
    idempotency_store.clear()
    web_module.app.dependency_overrides.clear()


@pytest.fixture()
def api_client(api_app):
    with TestClient(api_app) as client:
        yield client


def test_openapi_schema_exposes_versioned_public_contract(api_app):
    schema = api_app.openapi()

    assert schema["info"]["version"] == __version__
    assert "/api/v1/upload" in schema["paths"]
    assert "/api/v1/progress/{record_id}" in schema["paths"]
    assert "/api/v1/record/{record_id}/publish/youtube/now" in schema["paths"]


def test_committed_openapi_artifact_matches_live_schema(api_app):
    artifact_path = Path(__file__).resolve().parents[1] / "docs" / "openapi" / "clipmato-v1.openapi.json"
    artifact = json.loads(artifact_path.read_text())

    assert artifact == api_app.openapi()


def test_versioned_upload_returns_machine_readable_error_with_correlation_id(api_client, api_app):
    file_io_service = DummyFileIOService(return_path="/tmp/clipmato-upload.wav")
    processing_service = DummyProcessingService()
    progress_service = DummyProgressService()
    project_preset_service = DummyProjectPresetService()

    api_app.dependency_overrides[get_file_io_service] = lambda: file_io_service
    api_app.dependency_overrides[get_processing_service] = lambda: processing_service
    api_app.dependency_overrides[get_progress_service] = lambda: progress_service
    api_app.dependency_overrides[get_project_preset_service] = lambda: project_preset_service

    response = api_client.post(
        "/api/v1/upload",
        headers={"X-Correlation-ID": "corr-123"},
        files={"file": ("clip.wav", BytesIO(b"not-audio"), "text/plain")},
        data={"remove_silence": "false"},
    )

    assert response.status_code == 415
    assert response.headers["X-Correlation-ID"] == "corr-123"

    body = response.json()
    assert body["correlation_id"] == "corr-123"
    assert body["error"]["code"] == "unsupported_media_type"
    assert body["error"]["status"] == 415
    assert body["error"]["message"]


def test_versioned_upload_is_idempotent_for_reused_key(api_client, api_app):
    file_io_service = DummyFileIOService(return_path="/tmp/clipmato-upload.wav")
    processing_service = DummyProcessingService()
    progress_service = DummyProgressService()
    project_preset_service = DummyProjectPresetService()

    api_app.dependency_overrides[get_file_io_service] = lambda: file_io_service
    api_app.dependency_overrides[get_processing_service] = lambda: processing_service
    api_app.dependency_overrides[get_progress_service] = lambda: progress_service
    api_app.dependency_overrides[get_project_preset_service] = lambda: project_preset_service

    def build_request_kwargs():
        return {
            "headers": {"Idempotency-Key": "upload-key-123"},
            "files": {"file": ("clip.wav", BytesIO(b"123456"), "audio/wav")},
            "data": {"remove_silence": "false"},
        }

    first = api_client.post("/api/v1/upload", **build_request_kwargs())
    second = api_client.post("/api/v1/upload", **build_request_kwargs())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.headers["X-Idempotency-Replayed"] == "true"
    assert file_io_service.saved_filenames == ["clip.wav"]
    assert len(processing_service.calls) == 1
