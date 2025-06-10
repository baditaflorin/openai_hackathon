from agents import Runner
from ..agents.distributor import distributor_agent

def distribute(audio_output: str) -> str:
    """Use the Distributor agent to publish the podcast episode."""
    result = Runner.run_sync(distributor_agent, audio_output)
    return result.final_output

async def distribute_async(audio_output: str) -> str:
    """Asynchronously use the Distributor agent to publish the podcast episode."""
    result = await Runner.run(distributor_agent, audio_output)
    return result.final_output