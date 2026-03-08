from typing import Any

from ..prompts import run_prompt_task_async
from ..utils.local_ai import extract_entities_basic


async def extract_entities_async(transcript: str) -> dict[str, list[str]]:
    """
    Use the Entity Extractor agent to pull people and locations from transcript.
    Returns a dict with "people" and "locations" lists.
    """
    fallback = extract_entities_basic(transcript)
    execution = await run_prompt_task_async(
        "entity_extraction",
        {"transcript": transcript},
        fallback_output=fallback,
    )
    data = execution.output
    return {
        "people": data.get("people", fallback["people"]),
        "locations": data.get("locations", fallback["locations"]),
    }


async def extract_entities_with_prompt_async(
    transcript: str,
    record_id: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Return extracted entities plus prompt run metadata for record storage."""
    fallback = extract_entities_basic(transcript)
    execution = await run_prompt_task_async(
        "entity_extraction",
        {"transcript": transcript},
        fallback_output=fallback,
        record_id=record_id,
    )
    data = execution.output
    return {
        "people": data.get("people", fallback["people"]),
        "locations": data.get("locations", fallback["locations"]),
    }, execution.summary
