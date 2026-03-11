from typing import Any

from ..prompts import run_prompt_task_async, run_prompt_task_sync
from ..utils.local_ai import generate_script_basic
from ..utils.project_context import compose_prompt_variables


def generate_script(topic: str, project_context: dict[str, Any] | None = None) -> str:
    """Use the prompt engine to create show notes and questions."""
    fallback = generate_script_basic(topic)
    execution = run_prompt_task_sync(
        "script_generation",
        compose_prompt_variables({"transcript": topic}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def generate_script_async(topic: str, project_context: dict[str, Any] | None = None) -> str:
    """Asynchronously use the prompt engine to create show notes and questions."""
    fallback = generate_script_basic(topic)
    execution = await run_prompt_task_async(
        "script_generation",
        compose_prompt_variables({"transcript": topic}, project_context),
        fallback_output=fallback,
    )
    return execution.output or fallback


async def generate_script_with_prompt_async(
    topic: str,
    project_context: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return generated script plus prompt run metadata for record storage."""
    fallback = generate_script_basic(topic)
    execution = await run_prompt_task_async(
        "script_generation",
        compose_prompt_variables({"transcript": topic}, project_context),
        fallback_output=fallback,
        record_id=record_id,
    )
    return execution.output or fallback, execution.summary
