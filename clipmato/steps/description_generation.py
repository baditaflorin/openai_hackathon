from typing import Any

from ..prompts import run_prompt_task_async
from ..utils.local_ai import describe_transcript_basic
from ..utils.project_context import compose_prompt_variables


async def generate_descriptions_async(
    transcript: str,
    project_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Use the Description Generator agent to create short and long descriptions.
    Returns a dict with "short_description" and "long_description".
    """
    fallback = describe_transcript_basic(transcript)
    execution = await run_prompt_task_async(
        "description_generation",
        compose_prompt_variables({"transcript": transcript}, project_context),
        fallback_output=fallback,
    )
    data = execution.output
    return {
        "short_description": data.get("short_description", fallback["short_description"]),
        "long_description": data.get("long_description", fallback["long_description"]),
    }


async def generate_descriptions_with_prompt_async(
    transcript: str,
    project_context: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Return descriptions plus prompt run metadata for record storage."""
    fallback = describe_transcript_basic(transcript)
    execution = await run_prompt_task_async(
        "description_generation",
        compose_prompt_variables({"transcript": transcript}, project_context),
        fallback_output=fallback,
        record_id=record_id,
    )
    data = execution.output
    return {
        "short_description": data.get("short_description", fallback["short_description"]),
        "long_description": data.get("long_description", fallback["long_description"]),
    }, execution.summary
