import json
from ..agents.entity_extractor import entity_extractor_agent
from .step_utils import run_agent_async


async def extract_entities_async(transcript: str) -> dict[str, list[str]]:
    """
    Use the Entity Extractor agent to pull people and locations from transcript.
    Returns a dict with "people" and "locations" lists.
    """
    data = await run_agent_async(
        entity_extractor_agent,
        transcript,
        default={},
        parse_fn=json.loads,
    )
    return {
        "people": data.get("people", []),
        "locations": data.get("locations", []),
    }