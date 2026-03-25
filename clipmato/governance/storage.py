"""Persistent storage for agent governance records."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from ..config import AGENT_EVALUATIONS_PATH, PROMPT_RELEASE_STATE_PATH


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


def _default_prompt_release_state() -> dict[str, Any]:
    return {
        "live_defaults": {},
        "canaries": {},
        "history": [],
    }


def append_agent_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    """Append one agent governance evaluation record."""
    return _append_jsonl(AGENT_EVALUATIONS_PATH, payload)


def read_agent_evaluations(
    *,
    subject_type: str | None = None,
    task: str | None = None,
    prompt_version: str | None = None,
    record_id: str | None = None,
    action: str | None = None,
) -> list[dict[str, Any]]:
    """Read stored governance evaluations with optional filters."""
    with _storage_lock:
        records = _read_jsonl_unlocked(AGENT_EVALUATIONS_PATH)
    if subject_type is not None:
        records = [item for item in records if item.get("subject_type") == subject_type]
    if task is not None:
        records = [item for item in records if item.get("task") == task]
    if prompt_version is not None:
        records = [item for item in records if item.get("prompt_version") == prompt_version]
    if record_id is not None:
        records = [item for item in records if item.get("record_id") == record_id]
    if action is not None:
        records = [item for item in records if item.get("action") == action]
    return copy.deepcopy(records)


def read_prompt_release_state() -> dict[str, Any]:
    """Read the persisted live prompt release state."""
    with _storage_lock:
        if not PROMPT_RELEASE_STATE_PATH.exists():
            return _default_prompt_release_state()
        payload = json.loads(PROMPT_RELEASE_STATE_PATH.read_text(encoding="utf-8"))
    state = _default_prompt_release_state()
    state.update(payload or {})
    state["live_defaults"] = dict(state.get("live_defaults") or {})
    state["canaries"] = dict(state.get("canaries") or {})
    state["history"] = list(state.get("history") or [])
    return copy.deepcopy(state)


def write_prompt_release_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist the live prompt release state atomically."""
    state = _default_prompt_release_state()
    state.update(copy.deepcopy(payload))
    state["live_defaults"] = dict(state.get("live_defaults") or {})
    state["canaries"] = dict(state.get("canaries") or {})
    state["history"] = list(state.get("history") or [])
    with _storage_lock:
        PROMPT_RELEASE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROMPT_RELEASE_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return copy.deepcopy(state)
