"""
Define individual podcast production pipeline steps as reusable functions.
"""
from agents import Runner

from .agents.content_curator import content_curator_agent
from .agents.script_writer import script_writer_agent
from .agents.audio_editor import audio_editor_agent
from .agents.distributor import distributor_agent
import os
import subprocess
from pathlib import Path
from openai import OpenAI

# ffmpeg-based conversion to ensure Whisper-supported audio formats
SUPPORTED_AUDIO_EXTENSIONS = {
    "flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"
}

# Instantiate an OpenAI client (reads API key from OPENAI_API_KEY env var)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def curate_content(prompt: str) -> str:
    """Use the Content Curator agent to suggest a podcast topic."""
    result = Runner.run_sync(content_curator_agent, prompt)
    return result.final_output


def generate_script(topic: str) -> str:
    """Use the Script Writer agent to create show notes and questions."""
    result = Runner.run_sync(script_writer_agent, topic)
    return result.final_output


def edit_audio(audio_input: str) -> str:
    """Use the Audio Editor agent to perform basic audio cleanup."""
    result = Runner.run_sync(audio_editor_agent, audio_input)
    return result.final_output


def distribute(audio_output: str) -> str:
    """Use the Distributor agent to publish the podcast episode."""
    result = Runner.run_sync(distributor_agent, audio_output)
    return result.final_output

async def curate_content_async(prompt: str) -> str:
    """Asynchronously use the Content Curator agent to suggest a podcast topic."""
    result = await Runner.run(content_curator_agent, prompt)
    return result.final_output

async def generate_script_async(topic: str) -> str:
    """Asynchronously use the Script Writer agent to create show notes and questions."""
    result = await Runner.run(script_writer_agent, topic)
    return result.final_output

async def edit_audio_async(audio_input: str) -> str:
    """Asynchronously use the Audio Editor agent to perform basic audio cleanup."""
    result = await Runner.run(audio_editor_agent, audio_input)
    return result.final_output

async def distribute_async(audio_output: str) -> str:
    """Asynchronously use the Distributor agent to publish the podcast episode."""
    result = await Runner.run(distributor_agent, audio_output)
    return result.final_output

def transcribe_audio(audio_path: str, model: str = "whisper-1") -> str:
    """Transcribe an audio file to text using OpenAI's Whisper model."""
    # convert unsupported formats to a Whisper-friendly codec (e.g. WAV)
    src = Path(audio_path)
    if src.suffix.lower().lstrip('.') not in SUPPORTED_AUDIO_EXTENSIONS:
        dst = src.with_suffix('.wav')
        subprocess.run(
            [
                'ffmpeg', '-y', '-i', str(src),
                str(dst)
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        audio_path = str(dst)

    with open(audio_path, "rb") as audio_file:
        # Use the OpenAI Python v1.x interface for audio transcription
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="text",
        )
    return response