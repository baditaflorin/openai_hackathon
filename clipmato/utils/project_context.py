"""Helpers for normalizing reusable project context and prompt hooks."""
from __future__ import annotations

from typing import Any


PROJECT_PROMPT_DEFAULTS = {
    "project_name": "",
    "project_summary": "",
    "project_topics": "",
    "project_prompt_prefix": "",
    "project_prompt_suffix": "",
    "project_context_block": "",
}


def _normalize_text(value: Any) -> str:
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
        topic = _normalize_text(candidate)
        if not topic:
            continue
        key = topic.casefold()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)
    return topics


def normalize_project_context(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a compact project context payload or None when empty."""
    source = payload or {}
    project_name = _normalize_text(source.get("project_name"))
    project_summary = _normalize_text(source.get("project_summary"))
    project_topics = _normalize_topics(source.get("project_topics"))
    project_prompt_prefix = _normalize_text(source.get("project_prompt_prefix"))
    project_prompt_suffix = _normalize_text(source.get("project_prompt_suffix"))

    if not any((project_name, project_summary, project_topics, project_prompt_prefix, project_prompt_suffix)):
        return None

    return {
        "project_name": project_name,
        "project_summary": project_summary,
        "project_topics": project_topics,
        "project_prompt_prefix": project_prompt_prefix,
        "project_prompt_suffix": project_prompt_suffix,
    }


def build_project_prompt_variables(project_context: dict[str, Any] | None) -> dict[str, str]:
    """Return prompt variables for reusable project context and hooks."""
    normalized = normalize_project_context(project_context)
    if not normalized:
        return dict(PROJECT_PROMPT_DEFAULTS)

    lines = ["Project context:"]
    if normalized["project_name"]:
        lines.append(f"- Name: {normalized['project_name']}")
    if normalized["project_summary"]:
        lines.append(f"- Summary: {normalized['project_summary']}")
    if normalized["project_topics"]:
        lines.append(f"- Topics: {', '.join(normalized['project_topics'])}")
    lines.append("- Apply this context when shaping titles, descriptions, and surrounding copy.")

    return {
        "project_name": normalized["project_name"],
        "project_summary": normalized["project_summary"],
        "project_topics": ", ".join(normalized["project_topics"]),
        "project_prompt_prefix": normalized["project_prompt_prefix"],
        "project_prompt_suffix": normalized["project_prompt_suffix"],
        "project_context_block": "\n".join(lines),
    }


def compose_prompt_variables(base: dict[str, Any], project_context: dict[str, Any] | None) -> dict[str, Any]:
    """Merge task inputs with project-aware prompt variables."""
    return {
        **PROJECT_PROMPT_DEFAULTS,
        **base,
        **build_project_prompt_variables(project_context),
    }


def build_project_helper_text(project_context: dict[str, Any] | None) -> dict[str, str]:
    """Create concise UI helper strings derived from project context."""
    normalized = normalize_project_context(project_context)
    if not normalized:
        return {
            "title_helper": "",
            "subtitle_helper": "",
        }

    title_parts = [part for part in (normalized["project_name"], normalized["project_summary"]) if part]
    subtitle_parts: list[str] = []
    if normalized["project_topics"]:
        subtitle_parts.append(f"Topics: {', '.join(normalized['project_topics'])}")
    if normalized["project_prompt_prefix"]:
        subtitle_parts.append(f"Pre-hook: {normalized['project_prompt_prefix']}")
    if normalized["project_prompt_suffix"]:
        subtitle_parts.append(f"Post-hook: {normalized['project_prompt_suffix']}")

    return {
        "title_helper": " | ".join(title_parts[:2]),
        "subtitle_helper": " | ".join(subtitle_parts[:2]),
    }
