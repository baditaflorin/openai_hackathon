"""
Configuration constants for Clipmato: template paths, static files,
uploads directory, metadata file, progress mapping, and default parameters.
"""
from pathlib import Path

# Base directory of the Clipmato package
BASE_DIR = Path(__file__).parent

# Templates and static files
from fastapi.templating import Jinja2Templates
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
STATIC_DIR = BASE_DIR / "static"

# Uploads and metadata paths
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
METADATA_PATH = UPLOAD_DIR / "metadata.json"
ALLOWED_UPLOAD_MIME_TYPES: set[str] = {
    "audio/flac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/webm",
    "audio/x-wav",
}
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit for uploads

# Mapping of pipeline stages to progress percentages
STAGE_PROGRESS: dict[str, int] = {
    "transcribing": 20,
    "descriptions": 30,
    "entities": 40,
    "titles": 50,
    "script": 60,
    "remove_silence": 65,
    "editing": 75,
    "distribution": 90,
    "complete": 100,
}

# Silence-removal defaults (milliseconds/db)
MIN_SILENCE_LEN_MS = 1000
SILENCE_THRESH_DB = -50
KEEP_SILENCE_MS = 200

# Transcription defaults and FFmpeg parameters
AUDIO_ONLY_EXTENSIONS = {"flac", "m4a", "mp3", "mpga", "oga", "ogg", "wav"}
WHISPER_MODEL = "whisper-1"
MAX_CHUNK_SIZE_BYTES = 25 * 1024 * 1024  # 25MB limit for Whisper API
FFMPEG_AUDIO_CODEC = "pcm_s16le"
FFMPEG_SAMPLE_RATE = 16000
FFMPEG_CHANNELS = 1

# Scheduling defaults
DEFAULT_CADENCE = "daily"
CADENCE_INTERVALS: dict[str, dict[str, int]] = {
    DEFAULT_CADENCE: {"days": 1},
    "weekly": {"weeks": 1},
}
DEFAULT_PUBLISH_HOUR = 9
