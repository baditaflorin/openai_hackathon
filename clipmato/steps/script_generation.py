from agents import Runner
from ..agents.script_writer import script_writer_agent

def generate_script(topic: str) -> str:
    """Use the Script Writer agent to create show notes and questions."""
    result = Runner.run_sync(script_writer_agent, topic)
    return result.final_output

async def generate_script_async(topic: str) -> str:
    """Asynchronously use the Script Writer agent to create show notes and questions."""
    result = await Runner.run(script_writer_agent, topic)
    return result.final_output