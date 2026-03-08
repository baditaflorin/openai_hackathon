from typing import Any

from ..prompts import run_prompt_task_async, run_prompt_task_sync
from ..utils.local_ai import generate_script_basic


def generate_script(topic: str) -> str:
    """Use the prompt engine to create show notes and questions."""
    fallback = generate_script_basic(topic)
    execution = run_prompt_task_sync(
        "script_generation",
        {"transcript": topic},
        fallback_output=fallback,
    )
    return execution.output or fallback


async def generate_script_async(topic: str) -> str:
    """Asynchronously use the prompt engine to create show notes and questions."""
    fallback = generate_script_basic(topic)
    execution = await run_prompt_task_async(
        "script_generation",
        {"transcript": topic},
        fallback_output=fallback,
    )
    return execution.output or fallback


async def generate_script_with_prompt_async(
    topic: str,
    record_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return generated script plus prompt run metadata for record storage."""
    fallback = generate_script_basic(topic)
    execution = await run_prompt_task_async(
        "script_generation",
        {"transcript": topic},
        fallback_output=fallback,
        record_id=record_id,
    )
    return execution.output or fallback, execution.summary
