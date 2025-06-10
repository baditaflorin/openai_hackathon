from agents import Runner
from ..agents.content_curator import content_curator_agent

def curate_content(prompt: str) -> str:
    """Use the Content Curator agent to suggest a podcast topic."""
    result = Runner.run_sync(content_curator_agent, prompt)
    return result.final_output

async def curate_content_async(prompt: str) -> str:
    """Asynchronously use the Content Curator agent to suggest a podcast topic."""
    result = await Runner.run(content_curator_agent, prompt)
    return result.final_output