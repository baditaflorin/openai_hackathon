import os
import subprocess
import math
import tempfile
from functools import lru_cache

from pathlib import Path
import logging
from openai import OpenAI

from ..config import (
    AUDIO_ONLY_EXTENSIONS,
    MAX_CHUNK_SIZE_BYTES,
    WHISPER_MODEL,
    LOCAL_WHISPER_MODEL,
    FFMPEG_SAMPLE_RATE,
    FFMPEG_CHANNELS,
    FFMPEG_AUDIO_CODEC,
)
from ..runtime import (
    detect_local_whisper_device,
    local_whisper_installed,
    resolve_transcription_backend,
)

logger = logging.getLogger(__name__)


def _openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it, or use "
            "CLIPMATO_TRANSCRIPTION_BACKEND=local-whisper for host-native transcription."
        )
    return OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")


@lru_cache(maxsize=4)
def _load_local_whisper_model(model_name: str, device: str):
    if not local_whisper_installed():
        raise RuntimeError(
            "Local Whisper support is not installed. Install "
            "`pip install -e '.[local-transcription]'` to enable it."
        )

    import whisper

    logger.info(
        "transcribe_audio: loading local Whisper model '%s' on device '%s'",
        model_name,
        device,
    )
    return whisper.load_model(model_name, device=device)


def _prepare_audio_file(audio_path: str) -> Path:
    src = Path(audio_path)
    logger.info("transcribe_audio: input file %s", src)
    if src.suffix.lower().lstrip(".") in AUDIO_ONLY_EXTENSIONS:
        return src

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
            "No audio track detected. Please record with a microphone or choose "
            "webcam/screen+webcam recording."
        )

    dst = src.with_suffix(".wav")
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
        logger.error("transcribe_audio: audio conversion failed: %s", err)
        raise RuntimeError(f"Audio conversion failed: {err}")
    return dst


def _transcribe_with_openai(src: Path, model: str) -> str:
    client = _openai_client()
    file_size = src.stat().st_size
    logger.info("transcribe_audio: file size %d bytes", file_size)
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
                logger.info("transcribe_audio: transcribing chunk %s", chunk_file.name)
                with open(chunk_file, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        response_format="text",
                    )
                transcripts.append(response)
                logger.info("transcribe_audio: completed chunk %s", chunk_file.name)
        return "\n".join(transcripts)

    with open(src, "rb") as audio_file:
        logger.info("transcribe_audio: file size within limit, performing direct transcription")
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="text",
        )
    logger.info("transcribe_audio: direct transcription complete")
    return response


def _transcribe_with_local_whisper(src: Path) -> str:
    model_name = LOCAL_WHISPER_MODEL
    device = detect_local_whisper_device()
    logger.info(
        "transcribe_audio: using local Whisper model '%s' on device '%s'",
        model_name,
        device,
    )
    model = _load_local_whisper_model(model_name, device)
    result = model.transcribe(str(src), fp16=device == "cuda", verbose=False)
    return (result.get("text") or "").strip()

def transcribe_audio(audio_path: str, model: str = WHISPER_MODEL) -> str:
    """
    Transcribe an audio file to text using either OpenAI Whisper or a
    local Whisper model depending on runtime configuration.
    """
    src = _prepare_audio_file(audio_path)
    backend = resolve_transcription_backend()
    logger.info("transcribe_audio: resolved backend '%s'", backend)
    if backend == "local-whisper":
        return _transcribe_with_local_whisper(src)
    return _transcribe_with_openai(src, model=model)
