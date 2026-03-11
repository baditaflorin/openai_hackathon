from typing import Any

from ..prompts import run_prompt_task_async, run_prompt_task_sync
from ..utils.local_ai import distribute_basic
from ..utils.project_context import compose_prompt_variables


def distribute(audio_output: str, project_context: dict[str, Any] | None = None) -> str:
    """Use the prompt engine to produce distribution guidance."""
    fallback = distribute_basic(audio_output)
    execution = run_prompt_task_sync(
        "distribution_generation",
        compose_prompt_variables({"audio_output": audio_output}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def distribute_async(audio_output: str, project_context: dict[str, Any] | None = None) -> str:
    """Asynchronously use the prompt engine to produce distribution guidance."""
    fallback = distribute_basic(audio_output)
    execution = await run_prompt_task_async(
        "distribution_generation",
        compose_prompt_variables({"audio_output": audio_output}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def distribute_with_prompt_async(
    audio_output: str,
    project_context: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return distribution guidance plus prompt run metadata for record storage."""
    fallback = distribute_basic(audio_output)
    execution = await run_prompt_task_async(
        "distribution_generation",
        compose_prompt_variables({"audio_output": audio_output}, project_context),
        fallback_output=fallback,
        record_id=record_id,
    )
    return execution.output or fallback, execution.summary
