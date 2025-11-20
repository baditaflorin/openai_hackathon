import json
from pathlib import Path
from typing import Any

from .file_io import upload_dir
from ..config import STAGE_PROGRESS


def get_status_file(record_id: str) -> Path:
    """Return the path to the status file for a given record ID."""
    return Path(upload_dir) / f"{record_id}.status.json"


def update_progress(record_id: str, stage: str, message: str | None = None) -> None:
    """Write the current stage, its mapped percentage, and optional message to the status file."""
    percent = STAGE_PROGRESS.get(stage, 0)
    status: dict[str, object] = {"stage": stage, "progress": percent}
    if message:
        status["message"] = message
    _atomic_write(get_status_file(record_id), status)


def read_progress(record_id: str) -> dict:
    """Read and return the progress status for a given record ID."""
    status_file = get_status_file(record_id)
    if status_file.exists():
        try:
            raw_status = json.loads(status_file.read_text())
            return _validate_status(raw_status)
        except Exception:
            return {
                "stage": "error",
                "progress": 0,
                "error": "invalid_progress_file",
                "message": "Progress data is unreadable. Please retry or restart this job.",
            }
    return {"stage": "pending", "progress": 0}


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON data to ``path`` to avoid partial writes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data))
    tmp_path.replace(path)


def _validate_status(raw: Any) -> dict[str, Any]:
    """
    Validate a parsed progress payload and normalize it for the API/UI layer.

    Raises:
        ValueError: if the payload does not contain the expected schema/types.
    """

    if not isinstance(raw, dict):
        raise ValueError("Status payload must be a mapping")

    stage = raw.get("stage")
    progress = raw.get("progress")
    message = raw.get("message")

    if not isinstance(stage, str):
        raise ValueError("Status stage must be a string")
    if not isinstance(progress, (int, float)):
        raise ValueError("Status progress must be numeric")
    if message is not None and not isinstance(message, str):
        raise ValueError("Status message must be a string when provided")

    status: dict[str, Any] = {"stage": stage, "progress": progress}
    if message:
        status["message"] = message
    if "error" in raw and isinstance(raw["error"], str):
        status["error"] = raw["error"]
    return status
    
def enrich_with_progress(records: list[dict]) -> list[dict]:
    """
    Merge each record dict with its current progress status (stage & percentage).
    """
    enriched = []
    for rec in records:
        status = read_progress(rec.get("id", ""))
        merged = {**rec, **status}
        enriched.append(merged)
    return enriched
