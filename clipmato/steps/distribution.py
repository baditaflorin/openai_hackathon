from ..agents.distributor import distributor_agent
from .step_utils import run_agent_async, run_agent_sync


def distribute(audio_output: str) -> str:
    """Use the Distributor agent to publish the podcast episode."""
    return run_agent_sync(
        distributor_agent,
        audio_output,
        default="",
    )


async def distribute_async(audio_output: str) -> str:
    """Asynchronously use the Distributor agent to publish the podcast episode."""
    return await run_agent_async(
        distributor_agent,
        audio_output,
        default="",
    )