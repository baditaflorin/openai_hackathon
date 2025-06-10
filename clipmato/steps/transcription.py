import os
import subprocess
import math
import tempfile

import os
import subprocess
import math
import tempfile

from pathlib import Path
import logging
from openai import OpenAI

from ..config import (
    AUDIO_ONLY_EXTENSIONS,
    MAX_CHUNK_SIZE_BYTES,
    WHISPER_MODEL,
    FFMPEG_SAMPLE_RATE,
    FFMPEG_CHANNELS,
    FFMPEG_AUDIO_CODEC,
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.openai.com/v1"
)
logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str, model: str = WHISPER_MODEL) -> str:
    """
    Transcribe an audio file to text using OpenAI's Whisper model.
    Audio files larger than MAX_CHUNK_SIZE_BYTES will be split into
    smaller segments, transcribed sequentially, and recombined.
    """
    src = Path(audio_path)
    logger.info(f"transcribe_audio: input file {src}")
    # Convert any non-audio-only file (e.g. video container) to WAV for Whisper
    if src.suffix.lower().lstrip('.') not in AUDIO_ONLY_EXTENSIONS:
        logger.info("transcribe_audio: non-audio-only format detected, converting to WAV")
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0", str(src),
            ],
            capture_output=True,
            text=True,
        )
        if not probe.stdout.strip():
            raise RuntimeError(
                "No audio track detected. "
                "Please record with a microphone or choose webcam/screen+webcam recording."
            )
        dst = src.with_suffix('.wav')
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-vn", "-acodec", FFMPEG_AUDIO_CODEC,
                "-ar", str(FFMPEG_SAMPLE_RATE),
                "-ac", str(FFMPEG_CHANNELS),
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            logger.error(f"transcribe_audio: audio conversion failed: {err}")
            raise RuntimeError(f"Audio conversion failed: {err}")
        audio_path = str(dst)
        src = Path(audio_path)

    file_size = src.stat().st_size
    logger.info(f"transcribe_audio: file size {file_size} bytes")
    if file_size > MAX_CHUNK_SIZE_BYTES:
        logger.info(
            "transcribe_audio: file exceeds max chunk size (%d bytes), splitting audio",
            MAX_CHUNK_SIZE_BYTES,
        )
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
            logger.info(
                "transcribe_audio: splitting into chunks with pattern %s, segment_time %ds",
                pattern,
                chunk_duration,
            )
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
            )
            for chunk_file in sorted(Path(tmpdir).glob(f"chunk_*{src.suffix}")):
                logger.info(f"transcribe_audio: transcribing chunk {chunk_file.name}")
                with open(chunk_file, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        response_format="text",
                    )
                transcripts.append(response)
                logger.info(f"transcribe_audio: completed chunk {chunk_file.name}")
        return "\n".join(transcripts)

    with open(audio_path, "rb") as audio_file:
        logger.info("transcribe_audio: file size within limit, performing direct transcription")
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="text",
        )
    logger.info("transcribe_audio: direct transcription complete")
    return response