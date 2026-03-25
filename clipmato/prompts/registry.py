"""Prompt definition registry backed by packaged JSON assets."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from ..governance.release_rollout import resolve_release_version

PROMPT_DEFINITIONS_PACKAGE = "clipmato.prompts.definitions"


@dataclass(frozen=True, slots=True)
class PromptVersion:
    """One concrete prompt definition for a task."""

    task: str
    label: str
    version: str
    status: str
    owner: str
    created_at: str
    system_instructions: str
    user_template: str
    output_contract: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.task}@{self.version}"


@dataclass(frozen=True, slots=True)
class PromptTask:
    """Prompt task with one promoted default version and any variants."""

    task: str
    label: str
    owner: str
    default_version: str
    versions: dict[str, PromptVersion]


def _task_env_name(task: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", task.upper()).strip("_")
    return f"CLIPMATO_PROMPT_{normalized}_VERSION"


def _load_task_definition(payload: dict[str, Any]) -> PromptTask:
    task = str(payload["task"])
    versions: dict[str, PromptVersion] = {}
    for raw_version in payload.get("versions", []):
        version = PromptVersion(
            task=task,
            label=str(raw_version.get("label") or payload.get("label") or task.replace("_", " ").title()),
            version=str(raw_version["version"]),
            status=str(raw_version.get("status", "draft")),
            owner=str(raw_version.get("owner") or payload.get("owner") or "clipmato"),
            created_at=str(raw_version.get("created_at") or payload.get("created_at") or ""),
            system_instructions=str(raw_version.get("system_instructions") or ""),
            user_template=str(raw_version.get("user_template") or "{input}"),
            output_contract=dict(raw_version.get("output_contract") or {}),
        )
        versions[version.version] = version
    if not versions:
        raise ValueError(f"Prompt task {task} does not define any versions")
    default_version = str(payload.get("default_version") or next(iter(versions)))
    if default_version not in versions:
        raise ValueError(f"Prompt task {task} default version {default_version} is missing")
    return PromptTask(
        task=task,
        label=str(payload.get("label") or task.replace("_", " ").title()),
        owner=str(payload.get("owner") or "clipmato"),
        default_version=default_version,
        versions=versions,
    )


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, PromptTask]:
    registry: dict[str, PromptTask] = {}
    for resource in resources.files(PROMPT_DEFINITIONS_PACKAGE).iterdir():
        if resource.name.startswith("_") or resource.suffix != ".json":
            continue
        payload = json.loads(resource.read_text(encoding="utf-8"))
        task = _load_task_definition(payload)
        registry[task.task] = task
    return registry


def list_prompt_tasks() -> list[PromptTask]:
    """Return every registered prompt task."""
    return list(_load_registry().values())


def get_prompt_task(task: str) -> PromptTask:
    """Fetch a prompt task by key."""
    try:
        return _load_registry()[task]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt task: {task}") from exc


def list_prompt_versions(task: str) -> list[PromptVersion]:
    """Return all versions configured for a task."""
    prompt_task = get_prompt_task(task)
    return list(prompt_task.versions.values())


def resolve_prompt_version(
    task: str,
    requested_version: str | None = None,
    *,
    rollout_key: str | None = None,
) -> PromptVersion:
    """Resolve the active prompt version for a task."""
    prompt_task = get_prompt_task(task)
    version_key = (
        requested_version
        or os.getenv(_task_env_name(task), "").strip()
        or resolve_release_version(
            task,
            prompt_task.default_version,
            prompt_task.versions,
            rollout_key=rollout_key,
        )
    )
    try:
        return prompt_task.versions[version_key]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt version for {task}: {version_key}") from exc
