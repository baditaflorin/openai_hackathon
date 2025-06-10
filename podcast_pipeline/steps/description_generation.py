import json
from agents import Runner
from ..agents.description_generator import description_generator_agent


async def generate_descriptions_async(transcript: str) -> dict[str, str]:
    """
    Use the Description Generator agent to create short and long descriptions.
    Returns a dict with "short_description" and "long_description".
    """
    result = await Runner.run(description_generator_agent, transcript)
    try:
        data = json.loads(result.final_output)
        return {
            "short_description": data.get("short_description", ""),
            "long_description": data.get("long_description", ""),
        }
    except Exception:
        return {"short_description": "", "long_description": ""}