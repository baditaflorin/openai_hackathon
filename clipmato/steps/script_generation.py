from ..agents.script_writer import script_writer_agent
from .step_utils import run_agent_async, run_agent_sync


def generate_script(topic: str) -> str:
    """Use the Script Writer agent to create show notes and questions."""
    return run_agent_sync(
        script_writer_agent,
        topic,
        default="",
    )


async def generate_script_async(topic: str) -> str:
    """Asynchronously use the Script Writer agent to create show notes and questions."""
    return await run_agent_async(
        script_writer_agent,
        topic,
        default="",
    )