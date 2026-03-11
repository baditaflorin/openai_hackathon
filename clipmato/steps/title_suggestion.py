from typing import Any

from ..prompts import run_prompt_task_async, run_prompt_task_sync
from ..utils.project_context import compose_prompt_variables
from ..utils.local_ai import propose_titles_basic


def propose_titles(transcript: str, project_context: dict[str, Any] | None = None) -> list[str]:
    """Use the prompt engine to propose 5 episode titles."""
    fallback = propose_titles_basic(transcript)
    execution = run_prompt_task_sync(
        "title_suggestion",
        compose_prompt_variables({"transcript": transcript}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def propose_titles_async(transcript: str, project_context: dict[str, Any] | None = None) -> list[str]:
    """Asynchronously use the prompt engine to propose 5 episode titles."""
    fallback = propose_titles_basic(transcript)
    execution = await run_prompt_task_async(
        "title_suggestion",
        compose_prompt_variables({"transcript": transcript}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def propose_titles_with_prompt_async(
    transcript: str,
    project_context: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Return title suggestions plus prompt run metadata for record storage."""
    fallback = propose_titles_basic(transcript)
    execution = await run_prompt_task_async(
        "title_suggestion",
        compose_prompt_variables({"transcript": transcript}, project_context),
        fallback_output=fallback,
        record_id=record_id,
    )
    return execution.output or fallback, execution.summary
