"""Deterministic live prompt release resolution."""
from __future__ import annotations

import hashlib
from typing import Any

from .storage import read_prompt_release_state


def _stable_bucket(task: str, rollout_key: str) -> int:
    digest = hashlib.sha256(f"{task}:{rollout_key}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def resolve_release_version(
    task: str,
    packaged_default: str,
    available_versions: dict[str, Any],
    *,
    rollout_key: str | None = None,
) -> str:
    """Resolve the live prompt version with optional deterministic canary routing."""
    state = read_prompt_release_state()
    canary = dict((state.get("canaries") or {}).get(task) or {})
    if canary and rollout_key:
        candidate = str(canary.get("version") or "")
        percentage = max(min(int(canary.get("percentage", 0) or 0), 100), 0)
        if candidate in available_versions and percentage > 0 and _stable_bucket(task, rollout_key) < percentage:
            return candidate

    live_default = str((state.get("live_defaults") or {}).get(task) or "").strip()
    if live_default in available_versions:
        return live_default
    return packaged_default
