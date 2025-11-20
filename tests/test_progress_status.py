import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from clipmato.routers.upload import router
from clipmato.utils import file_io, progress


def _build_app():
    app = FastAPI()
    app.include_router(router)

    from clipmato.dependencies import (
        get_file_io_service,
        get_processing_service,
    )

    class DummyProcessing:
        async def process(self, *args, **kwargs):
            return None

    class DummyFileIO:
        def save(self, *args, **kwargs):
            return None

    app.dependency_overrides[get_file_io_service] = lambda: DummyFileIO()
    app.dependency_overrides[get_processing_service] = lambda: DummyProcessing()
    return app


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(file_io, "upload_dir", tmp_path, raising=False)
    monkeypatch.setattr(progress, "upload_dir", tmp_path, raising=False)
    return TestClient(_build_app())


def test_progress_reports_truncated_file_error(client, tmp_path):
    record_id = "abc123"
    status_path = tmp_path / f"{record_id}.status.json"
    status_path.write_text('{"stage": "transcribing"')

    response = client.get(f"/progress/{record_id}")
    body = response.json()

    assert body["stage"] == "error"
    assert body["progress"] == 0
    assert body["error"] == "invalid_progress_file"
    assert "unreadable" in body["message"].lower()


def test_progress_reports_invalid_schema_error(client, tmp_path):
    record_id = "xyz789"
    status_path = tmp_path / f"{record_id}.status.json"
    status_path.write_text(json.dumps({"stage": 5, "progress": "oops"}))

    response = client.get(f"/progress/{record_id}")
    body = response.json()

    assert body["stage"] == "error"
    assert body["progress"] == 0
    assert body["error"] == "invalid_progress_file"
    assert "unreadable" in body["message"].lower()
