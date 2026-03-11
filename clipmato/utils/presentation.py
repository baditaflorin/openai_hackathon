"""Presentation helpers for shared frontend context."""
from __future__ import annotations

from typing import Any

from .project_context import build_project_helper_text

PROMPT_TASK_LABELS = {
    "title_suggestion": "Title suggestions",
    "description_generation": "Descriptions",
    "entity_extraction": "Entities",
    "script_generation": "Script",
    "distribution_generation": "Distribution guidance",
}


def present_record(record: dict[str, Any]) -> dict[str, Any]:
    """Attach derived frontend fields to a record dict."""
    presented = dict(record)
    helper_text = build_project_helper_text(presented.get("project_context"))
    youtube_job = (presented.get("publish_jobs") or {}).get("youtube") or {}
    presented["youtube_job"] = youtube_job
    prompt_run_items: list[dict[str, Any]] = []
    for task_key, prompt_run in (presented.get("prompt_runs") or {}).items():
        item = dict(prompt_run)
        item["task_key"] = task_key
        item["task_label"] = PROMPT_TASK_LABELS.get(task_key, task_key.replace("_", " ").title())
        prompt_run_items.append(item)
    prompt_run_items.sort(key=lambda item: item["task_label"])
    presented["prompt_run_items"] = prompt_run_items
    presented["is_processing"] = presented.get("progress", 100) < 100 and not presented.get("error")
    presented["is_failed"] = bool(presented.get("error")) or presented.get("stage") == "error"
    presented["is_published"] = youtube_job.get("status") == "published"
    presented["display_title"] = presented.get("selected_title") or presented.get("filename") or "Untitled episode"
    presented["display_title_helper"] = helper_text["title_helper"]
    presented["display_subtitle_helper"] = helper_text["subtitle_helper"]
    return presented


def workflow_metrics(records: list[dict[str, Any]]) -> dict[str, int]:
    """Summarize the current workflow state for the shared app shell."""
    processing = 0
    scheduled = 0
    published = 0
    for rec in records:
        if rec.get("progress", 100) < 100 and not rec.get("error"):
            processing += 1
        if rec.get("schedule_time"):
            scheduled += 1
        youtube_job = rec.get("youtube_job") or (rec.get("publish_jobs") or {}).get("youtube") or {}
        if youtube_job.get("status") == "published":
            published += 1
    return {
        "episodes": len(records),
        "processing": processing,
        "scheduled": scheduled,
        "published": published,
    }
