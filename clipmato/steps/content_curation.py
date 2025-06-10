from ..agents.content_curator import content_curator_agent
from .step_utils import run_agent_async, run_agent_sync


def curate_content(prompt: str) -> str:
    """Use the Content Curator agent to suggest a podcast topic."""
    return run_agent_sync(
        content_curator_agent,
        prompt,
        default="",
    )


async def curate_content_async(prompt: str) -> str:
    """Asynchronously use the Content Curator agent to suggest a podcast topic."""
    return await run_agent_async(
        content_curator_agent,
        prompt,
        default="",
    )