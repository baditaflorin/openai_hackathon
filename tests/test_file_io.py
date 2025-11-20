from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from clipmato.utils import file_io


@pytest.fixture(autouse=True)
def isolate_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(file_io, "upload_dir", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)


def test_sanitize_filename_removes_paths_and_invalid_chars():
    sanitized = file_io.sanitize_filename("../unsafe/na/me?.wav")
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "?" not in sanitized


def test_save_upload_file_generates_unique_names(monkeypatch):
    monkeypatch.setattr(
        file_io, "ALLOWED_UPLOAD_MIME_TYPES", {"audio/wav"}, raising=False
    )
    content = b"12345"
    upload1 = UploadFile(
        filename="track.wav",
        file=BytesIO(content),
        headers={"content-type": "audio/wav"},
    )
    upload2 = UploadFile(
        filename="track.wav",
        file=BytesIO(content),
        headers={"content-type": "audio/wav"},
    )

    first_path = Path(file_io.save_upload_file(upload1))
    second_path = Path(file_io.save_upload_file(upload2))

    assert first_path.name != second_path.name
    assert first_path.exists()
    assert second_path.exists()


def test_save_upload_file_rejects_disallowed_mime(monkeypatch):
    monkeypatch.setattr(
        file_io, "ALLOWED_UPLOAD_MIME_TYPES", {"audio/wav"}, raising=False
    )
    upload = UploadFile(
        filename="track.wav",
        file=BytesIO(b"12345"),
        headers={"content-type": "text/plain"},
    )
    with pytest.raises(HTTPException) as exc:
        file_io.save_upload_file(upload)
    assert exc.value.status_code == 415


def test_save_upload_file_rejects_large_files(monkeypatch):
    monkeypatch.setattr(file_io, "MAX_UPLOAD_SIZE_BYTES", 5, raising=False)
    monkeypatch.setattr(
        file_io, "ALLOWED_UPLOAD_MIME_TYPES", {"audio/wav"}, raising=False
    )
    upload = UploadFile(
        filename="track.wav",
        file=BytesIO(b"123456789"),
        headers={"content-type": "audio/wav"},
    )
    with pytest.raises(HTTPException) as exc:
        file_io.save_upload_file(upload)
    assert exc.value.status_code == 413
    assert not list(file_io.upload_dir.iterdir())
