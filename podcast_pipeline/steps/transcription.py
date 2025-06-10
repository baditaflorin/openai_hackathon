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

def transcribe_audio(audio_path: str, model: str = "whisper-1") -> str:
    """Transcribe an audio file to text using OpenAI's Whisper model."""
    src = Path(audio_path)
    if src.suffix.lower().lstrip('.') not in SUPPORTED_AUDIO_EXTENSIONS:
        dst = src.with_suffix('.wav')
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(src), str(dst)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        audio_path = str(dst)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="text",
        )
    return response