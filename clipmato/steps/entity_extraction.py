import json
from agents import Runner
from ..agents.entity_extractor import entity_extractor_agent


async def extract_entities_async(transcript: str) -> dict[str, list[str]]:
    """
    Use the Entity Extractor agent to pull people and locations from transcript.
    Returns a dict with "people" and "locations" lists.
    """
    result = await Runner.run(entity_extractor_agent, transcript)
    try:
        data = json.loads(result.final_output)
        return {
            "people": data.get("people", []),
            "locations": data.get("locations", []),
        }
    except Exception:
        return {"people": [], "locations": []}