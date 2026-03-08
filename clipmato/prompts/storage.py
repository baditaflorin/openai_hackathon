"""Persistent storage for prompt runs and prompt evaluations."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from ..config import PROMPT_EVALUATIONS_PATH, PROMPT_RUNS_PATH


_storage_lock = RLock()


def _read_jsonl_unlocked(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _append_jsonl(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    entry = copy.deepcopy(payload)
    with _storage_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry))
            handle.write("\n")
    return entry


def append_prompt_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Append a prompt run to the durable run ledger."""
    return _append_jsonl(PROMPT_RUNS_PATH, payload)


def append_prompt_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    """Append a prompt evaluation signal to the durable evaluation ledger."""
    return _append_jsonl(PROMPT_EVALUATIONS_PATH, payload)


def read_prompt_runs(*, record_id: str | None = None, task: str | None = None) -> list[dict[str, Any]]:
    """Read prompt runs, optionally filtered by record or task."""
    with _storage_lock:
        records = _read_jsonl_unlocked(PROMPT_RUNS_PATH)
    if record_id is not None:
        records = [item for item in records if item.get("record_id") == record_id]
    if task is not None:
        records = [item for item in records if item.get("task") == task]
    return copy.deepcopy(records)


def read_prompt_evaluations(
    *,
    record_id: str | None = None,
    task: str | None = None,
) -> list[dict[str, Any]]:
    """Read prompt evaluations, optionally filtered by record or task."""
    with _storage_lock:
        records = _read_jsonl_unlocked(PROMPT_EVALUATIONS_PATH)
    if record_id is not None:
        records = [item for item in records if item.get("record_id") == record_id]
    if task is not None:
        records = [item for item in records if item.get("task") == task]
    return copy.deepcopy(records)
