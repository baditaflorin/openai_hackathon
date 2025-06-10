import json
from ..agents.description_generator import description_generator_agent
from .step_utils import run_agent_async


async def generate_descriptions_async(transcript: str) -> dict[str, str]:
    """
    Use the Description Generator agent to create short and long descriptions.
    Returns a dict with "short_description" and "long_description".
    """
    data = await run_agent_async(
        description_generator_agent,
        transcript,
        default={},
        parse_fn=json.loads,
    )
    return {
        "short_description": data.get("short_description", ""),
        "long_description": data.get("long_description", ""),
    }