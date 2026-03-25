"""Persistent file-backed storage for agent runs."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from ..config import AGENT_RUNS_DIR


_storage_lock = RLock()


class AgentRunStorage:
    """Store each agent run as its own JSON document."""

    def __init__(self, runs_dir: Path = AGENT_RUNS_DIR) -> None:
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        run = copy.deepcopy(payload)
        path = self._run_path(str(run["run_id"]))
        with _storage_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=f"{path.stem}_", suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(run, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, path)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
        return copy.deepcopy(run)

    def read(self, run_id: str) -> dict[str, Any] | None:
        path = self._run_path(run_id)
        if not path.exists():
            return None
        with _storage_lock:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return copy.deepcopy(payload) if isinstance(payload, dict) else None

    def list_runs(self, *, workflow: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        with _storage_lock:
            paths = sorted(self.runs_dir.glob("*.json"))
        runs: list[dict[str, Any]] = []
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            if workflow and payload.get("workflow") != workflow:
                continue
            runs.append(payload)
        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return copy.deepcopy(runs[:limit])
