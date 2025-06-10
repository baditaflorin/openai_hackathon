from pathlib import Path
from pydub import AudioSegment
from pydub.silence import split_on_silence
import logging

logger = logging.getLogger(__name__)

def remove_silence(
    audio_path: str,
    min_silence_len: int = 1000,
    silence_thresh: int = -50,
    keep_silence: int = 200,
) -> tuple[float, float, str]:
    """
    Remove silent chunks from an audio file.
    Returns a tuple of (original_duration_sec, trimmed_duration_sec, output_path).
    """
    src = Path(audio_path)
    logger.info(
        f"remove_silence: input={src}, min_silence_len={min_silence_len}, "
        f"silence_thresh={silence_thresh}, keep_silence={keep_silence}"
    )
    sound = AudioSegment.from_file(src)
    original_duration = len(sound) / 1000.0
    logger.info(f"remove_silence: original duration={original_duration:.2f}s")
    min_silence_len = int(min_silence_len)
    silence_thresh = int(silence_thresh)
    keep_silence = int(keep_silence)
    logger.info(
        f"remove_silence: splitting (min_silence_len={min_silence_len}, "
        f"silence_thresh={silence_thresh}, keep_silence={keep_silence})"
    )
    try:
        chunks = split_on_silence(
            sound,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence,
        )
    except Exception:
        logger.exception(f"remove_silence: split_on_silence failed for {src}")
        raise
    logger.info(f"remove_silence: {len(chunks)} chunks detected")
    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += chunk
    output_path = src.with_name(f"{src.stem}_trimmed{src.suffix}")
    combined.export(output_path, format=src.suffix.lstrip('.'))
    trimmed_duration = len(combined) / 1000.0
    logger.info(f"remove_silence: trimmed duration={trimmed_duration:.2f}s, output={output_path}")
    return original_duration, trimmed_duration, str(output_path)