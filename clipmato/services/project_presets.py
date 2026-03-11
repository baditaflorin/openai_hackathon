"""Persistent project preset storage and merge helpers."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import fcntl

from ..utils.project_context import normalize_project_context


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_topics(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = []
    topics: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        topic = _normalized_text(candidate)
        if not topic:
            continue
        key = topic.casefold()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)
    return topics


def _normalize_preset(payload: dict[str, Any], *, preset_id: str | None = None) -> dict[str, Any] | None:
    label = _normalized_text(payload.get("label") or payload.get("name"))
    project_context = normalize_project_context(
        {
            "project_name": payload.get("project_name") or label,
            "project_summary": payload.get("project_summary"),
            "project_topics": payload.get("project_topics"),
            "project_prompt_prefix": payload.get("project_prompt_prefix"),
            "project_prompt_suffix": payload.get("project_prompt_suffix"),
        }
    )
    if not label or not project_context:
        return None
    return {
        "id": preset_id or _normalized_text(payload.get("id")) or str(uuid4()),
        "label": label,
        **project_context,
    }


def _lock_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.lock")


@contextmanager
def _locked_file(path: Path):
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return copy.deepcopy(payload) if isinstance(payload, list) else []


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f"{path.stem}_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class ProjectPresetService:
    """Read, persist, and combine reusable project presets."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            from ..config import PROJECT_PRESETS_PATH

            path = PROJECT_PRESETS_PATH
        self.path = path

    def read_presets(self) -> list[dict[str, Any]]:
        with _locked_file(self.path):
            presets = _read_json(self.path)
        presets.sort(key=lambda item: item.get("label", "").casefold())
        return presets

    def save_preset(self, payload: dict[str, Any]) -> dict[str, Any]:
        preset = _normalize_preset(payload, preset_id=_normalized_text(payload.get("preset_id") or payload.get("id")) or None)
        if preset is None:
            raise ValueError("Project preset requires a label and at least one project detail.")

        with _locked_file(self.path):
            presets = _read_json(self.path)
            for index, existing in enumerate(presets):
                if existing.get("id") == preset["id"]:
                    presets[index] = preset
                    break
            else:
                presets.append(preset)
            presets.sort(key=lambda item: item.get("label", "").casefold())
            _write_json(self.path, presets)
        return copy.deepcopy(preset)

    def delete_preset(self, preset_id: str) -> dict[str, Any] | None:
        with _locked_file(self.path):
            presets = _read_json(self.path)
            for index, existing in enumerate(presets):
                if existing.get("id") == preset_id:
                    removed = presets.pop(index)
                    _write_json(self.path, presets)
                    return copy.deepcopy(removed)
        return None

    def get_presets(self, preset_ids: list[str]) -> list[dict[str, Any]]:
        wanted = {item for item in preset_ids if _normalized_text(item)}
        if not wanted:
            return []
        return [preset for preset in self.read_presets() if preset.get("id") in wanted]

    def merge_context(
        self,
        preset_ids: list[str] | None,
        manual_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        presets = self.get_presets(preset_ids or [])
        merged_topics: list[str] = []
        seen_topics: set[str] = set()
        project_names: list[str] = []
        summaries: list[str] = []
        prefixes: list[str] = []
        suffixes: list[str] = []

        for preset in presets:
            project_name = _normalized_text(preset.get("project_name"))
            if project_name and project_name not in project_names:
                project_names.append(project_name)
            summary = _normalized_text(preset.get("project_summary"))
            if summary and summary not in summaries:
                summaries.append(summary)
            prefix = _normalized_text(preset.get("project_prompt_prefix"))
            if prefix and prefix not in prefixes:
                prefixes.append(prefix)
            suffix = _normalized_text(preset.get("project_prompt_suffix"))
            if suffix and suffix not in suffixes:
                suffixes.append(suffix)
            for topic in _normalize_topics(preset.get("project_topics")):
                key = topic.casefold()
                if key in seen_topics:
                    continue
                seen_topics.add(key)
                merged_topics.append(topic)

        manual = manual_context or {}
        manual_topics = _normalize_topics(manual.get("project_topics"))
        for topic in manual_topics:
            key = topic.casefold()
            if key in seen_topics:
                continue
            seen_topics.add(key)
            merged_topics.append(topic)

        return normalize_project_context(
            {
                "project_name": _normalized_text(manual.get("project_name")) or " + ".join(project_names),
                "project_summary": _normalized_text(manual.get("project_summary")) or " ".join(summaries),
                "project_topics": merged_topics,
                "project_prompt_prefix": _normalized_text(manual.get("project_prompt_prefix")) or " ".join(prefixes),
                "project_prompt_suffix": _normalized_text(manual.get("project_prompt_suffix")) or " ".join(suffixes),
            }
        )
