import json
from pathlib import Path

from .file_io import upload_dir

# Mapping of pipeline stages to progress percentages
STAGE_PROGRESS: dict[str, int] = {
    "transcribing": 20,
    "descriptions": 30,
    "entities": 40,
    "titles": 50,
    "script": 60,
    "editing": 75,
    "distribution": 90,
    "complete": 100,
}


def get_status_file(record_id: str) -> Path:
    """Return the path to the status file for a given record ID."""
    return Path(upload_dir) / f"{record_id}.status.json"


def update_progress(record_id: str, stage: str) -> None:
    """Write the current stage and its mapped percentage to the status file."""
    percent = STAGE_PROGRESS.get(stage, 0)
    status = {"stage": stage, "progress": percent}
    get_status_file(record_id).write_text(json.dumps(status))


def read_progress(record_id: str) -> dict:
    """Read and return the progress status for a given record ID."""
    status_file = get_status_file(record_id)
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    return {"stage": "pending", "progress": 0}