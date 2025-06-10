from pathlib import Path
from pydub import AudioSegment
from pydub.silence import split_on_silence

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
    sound = AudioSegment.from_file(src)
    original_duration = len(sound) / 1000.0
    chunks = split_on_silence(
        sound,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence,
    )
    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += chunk
    output_path = src.with_name(f"{src.stem}_trimmed{src.suffix}")
    combined.export(output_path, format=src.suffix.lstrip('.'))
    trimmed_duration = len(combined) / 1000.0
    return original_duration, trimmed_duration, str(output_path)