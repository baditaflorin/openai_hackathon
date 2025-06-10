from pathlib import Path
from pydub import AudioSegment
from pydub.silence import split_on_silence

import logging

logger = logging.getLogger(__name__)

# Monkey-patch builtins.buffer for Python 3 compatibility in pydub.pyaudioop
import builtins
builtins.buffer = memoryview

# Monkey-patch pydub.pyaudioop._sample_count to use integer division (avoid float in range())
import pydub.pyaudioop as pyaudioop
pyaudioop._sample_count = lambda cp, size: len(cp) // size

from ..config import MIN_SILENCE_LEN_MS, SILENCE_THRESH_DB, KEEP_SILENCE_MS

def remove_silence(
    audio_path: str,
    min_silence_len: int = MIN_SILENCE_LEN_MS,
    silence_thresh: int = SILENCE_THRESH_DB,
    keep_silence: int = KEEP_SILENCE_MS,
) -> tuple[float, float, str]:
    """
    Remove silent chunks from an audio file.
    Returns a tuple of (original_duration_sec, trimmed_duration_sec, output_path).
    """
    src = Path(audio_path)
    logger.info(
        "remove_silence: input=%s, min_silence_len=%d, silence_thresh=%d, keep_silence=%d",
        src,
        min_silence_len,
        silence_thresh,
        keep_silence,
    )
    sound = AudioSegment.from_file(src)
    original_duration = len(sound) / 1000.0
    logger.info("remove_silence: original duration=%.2fs", original_duration)

    # enforce integer thresholds (avoid floats in pydub range)
    min_silence_len = int(min_silence_len)
    silence_thresh = int(silence_thresh)
    keep_silence = int(keep_silence)
    logger.info(
        "remove_silence: splitting (min_silence_len=%d, silence_thresh=%d, keep_silence=%d)",
        min_silence_len,
        silence_thresh,
        keep_silence,
    )
    try:
        chunks = split_on_silence(
            sound,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence,
        )
    except Exception:
        logger.exception("remove_silence: split_on_silence failed for %s", src)
        raise
    logger.info("remove_silence: %d chunks detected", len(chunks))

    # build empty segment matching source parameters to avoid sample-width mismatch
    combined = sound[:0]
    for chunk in chunks:
        combined += chunk
    output_path = src.with_name(f"{src.stem}_trimmed{src.suffix}")
    combined.export(output_path, format=src.suffix.lstrip('.'))
    trimmed_duration = len(combined) / 1000.0
    logger.info(
        "remove_silence: trimmed duration=%.2fs, output=%s",
        trimmed_duration,
        output_path,
    )
    return original_duration, trimmed_duration, str(output_path)