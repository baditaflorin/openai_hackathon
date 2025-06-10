from agents import Runner
from ..agents.audio_editor import audio_editor_agent

def edit_audio(audio_input: str) -> str:
    """Use the Audio Editor agent to perform basic audio cleanup."""
    result = Runner.run_sync(audio_editor_agent, audio_input)
    return result.final_output

async def edit_audio_async(audio_input: str) -> str:
    """Asynchronously use the Audio Editor agent to perform basic audio cleanup."""
    result = await Runner.run(audio_editor_agent, audio_input)
    return result.final_output