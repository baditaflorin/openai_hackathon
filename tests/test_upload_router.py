from io import BytesIO
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from clipmato.routers.upload import router
from clipmato.utils import file_io


class DummyFileIO:
    def __init__(self, save_callable):
        self.save = save_callable


def build_app(file_io_service):
    app = FastAPI()
    app.include_router(router)
    # Override only the file IO service; other dependencies use lightweight fallbacks
    from clipmato.dependencies import get_file_io_service, get_processing_service, get_progress_service

    class DummyProcessing:
        async def process(self, *args, **kwargs):
            return None

    class DummyProgress:
        def update(self, *args, **kwargs):
            return None

        def read(self, record_id):
            return {"stage": "pending", "progress": 0}

    app.dependency_overrides[get_file_io_service] = lambda: file_io_service
    app.dependency_overrides[get_processing_service] = lambda: DummyProcessing()
    app.dependency_overrides[get_progress_service] = lambda: DummyProgress()
    return app


def test_upload_rejects_disallowed_type(monkeypatch):
    monkeypatch.setattr(
        file_io, "ALLOWED_UPLOAD_MIME_TYPES", {"audio/wav"}, raising=False
    )
    # use real save implementation to exercise validation
    app = build_app(DummyFileIO(file_io.save_upload_file))
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={"file": ("clip.wav", BytesIO(b"12345"), "text/plain")},
        data={"remove_silence": "false"},
    )
    assert response.status_code == 415
    assert "Unsupported media type" in response.json()["detail"]


def test_upload_rejects_oversized_file(monkeypatch, tmp_path):
    monkeypatch.setattr(file_io, "MAX_UPLOAD_SIZE_BYTES", 5, raising=False)
    monkeypatch.setattr(
        file_io, "ALLOWED_UPLOAD_MIME_TYPES", {"audio/wav"}, raising=False
    )
    monkeypatch.setattr(file_io, "upload_dir", tmp_path, raising=False)

    app = build_app(DummyFileIO(file_io.save_upload_file))
    client = TestClient(app)

    response = client.post(
        "/upload",
        files={"file": ("clip.wav", BytesIO(b"123456789"), "audio/wav")},
        data={"remove_silence": "false"},
    )
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]
    assert not list(tmp_path.iterdir())
