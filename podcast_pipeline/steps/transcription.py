import os
import subprocess
import math
import tempfile

from pathlib import Path
from openai import OpenAI

# ffmpeg-based conversion to ensure Whisper-supported audio formats
SUPPORTED_AUDIO_EXTENSIONS = {
    "flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"
}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_CHUNK_SIZE_BYTES = 25 * 1024 * 1024  # 25MB limit for Whisper API

def transcribe_audio(audio_path: str, model: str = "whisper-1") -> str:
    """
    Transcribe an audio file to text using OpenAI's Whisper model.
    Audio files larger than 25MB will be split into smaller segments,
    transcribed sequentially, and recombined into a single transcript.
    """
    src = Path(audio_path)
    if src.suffix.lower().lstrip('.') not in SUPPORTED_AUDIO_EXTENSIONS:
        dst = src.with_suffix('.wav')
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(dst)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        audio_path = str(dst)
        src = Path(audio_path)

    file_size = src.stat().st_size
    if file_size > MAX_CHUNK_SIZE_BYTES:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(src),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = float(result.stdout.strip())
        num_chunks = math.ceil(file_size / MAX_CHUNK_SIZE_BYTES)
        chunk_duration = math.ceil(duration / num_chunks)

        transcripts: list[str] = []
        with tempfile.TemporaryDirectory(dir=src.parent) as tmpdir:
            pattern = Path(tmpdir) / f"chunk_%03d{src.suffix}"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src),
                    "-f",
                    "segment",
                    "-segment_time",
                    str(chunk_duration),
                    "-c",
                    "copy",
                    "-reset_timestamps",
                    "1",
                    str(pattern),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for chunk_file in sorted(Path(tmpdir).glob(f"chunk_*{src.suffix}")):
                with open(chunk_file, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        response_format="text",
                    )
                    transcripts.append(response)
        return "\n".join(transcripts)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="text",
        )
    return response