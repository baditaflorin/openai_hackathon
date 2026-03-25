"""
Configuration constants for Clipmato: template paths, static files,
uploads directory, metadata file, progress mapping, and default parameters.
"""
import os
from pathlib import Path

try:
    from fastapi.templating import Jinja2Templates
except ModuleNotFoundError:  # pragma: no cover - allows non-web service tests without FastAPI installed
    Jinja2Templates = None  # type: ignore[assignment]

# Base directory of the Clipmato package
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR_ENV_VAR = "CLIPMATO_DATA_DIR"
DEFAULT_DATA_DIR = (
    BASE_DIR / "uploads" if (BASE_DIR / "uploads").exists() else Path.home() / ".clipmato"
)

# Templates and static files
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates")) if Jinja2Templates is not None else None
STATIC_DIR = BASE_DIR / "static"

# Uploads and metadata paths. Runtime data can live outside the package so
# packaged installs and containers can persist uploads in a writable volume.
UPLOAD_DIR = Path(os.getenv(DATA_DIR_ENV_VAR, str(DEFAULT_DATA_DIR))).expanduser()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_BUILD_DIR = UPLOAD_DIR / ".static-build"
STATIC_BUILD_DIR.mkdir(parents=True, exist_ok=True)
METADATA_PATH = UPLOAD_DIR / "metadata.json"
PROVIDERS_DIR = UPLOAD_DIR / "providers"
PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = UPLOAD_DIR / "settings.json"
SECRETS_PATH = UPLOAD_DIR / "secrets.json"
PROMPT_RUNS_PATH = UPLOAD_DIR / "prompt_runs.jsonl"
PROMPT_EVALUATIONS_PATH = UPLOAD_DIR / "prompt_evaluations.jsonl"
PROJECT_PRESETS_PATH = UPLOAD_DIR / "project_presets.json"
AGENT_RUNS_DIR = UPLOAD_DIR / "agent_runs"
AGENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)

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
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
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
TRANSCRIPTION_BACKEND_ENV_VAR = "CLIPMATO_TRANSCRIPTION_BACKEND"
CONTENT_BACKEND_ENV_VAR = "CLIPMATO_CONTENT_BACKEND"
LOCAL_WHISPER_MODEL_ENV_VAR = "CLIPMATO_LOCAL_WHISPER_MODEL"
LOCAL_WHISPER_DEVICE_ENV_VAR = "CLIPMATO_LOCAL_WHISPER_DEVICE"
OLLAMA_BASE_URL_ENV_VAR = "CLIPMATO_OLLAMA_BASE_URL"
OLLAMA_MODEL_ENV_VAR = "CLIPMATO_OLLAMA_MODEL"
OLLAMA_TIMEOUT_ENV_VAR = "CLIPMATO_OLLAMA_TIMEOUT_SECONDS"
OPENAI_CONTENT_MODEL_ENV_VAR = "CLIPMATO_OPENAI_CONTENT_MODEL"
PUBLIC_BASE_URL_ENV_VAR = "CLIPMATO_BASE_URL"
GOOGLE_CLIENT_ID_ENV_VAR = "GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET_ENV_VAR = "GOOGLE_CLIENT_SECRET"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

# Scheduling defaults
DEFAULT_CADENCE = "daily"
CADENCE_INTERVALS: dict[str, dict[str, int]] = {
    DEFAULT_CADENCE: {"days": 1},
    "weekly": {"weeks": 1},
}
DEFAULT_PUBLISH_HOUR = 9

# Publishing runtime configuration
PUBLISH_POLL_SECONDS = max(int(os.getenv("CLIPMATO_PUBLISH_POLL_SECONDS", "15")), 5)
PUBLISH_MAX_ATTEMPTS = max(int(os.getenv("CLIPMATO_PUBLISH_MAX_ATTEMPTS", "3")), 1)
PUBLISH_RETRY_SECONDS = max(int(os.getenv("CLIPMATO_PUBLISH_RETRY_SECONDS", "300")), 30)
YOUTUBE_DEFAULT_PRIVACY_STATUS = (
    os.getenv("CLIPMATO_YOUTUBE_PRIVACY_STATUS", "private").strip().lower() or "private"
)
YOUTUBE_TOKEN_PATH = PROVIDERS_DIR / "youtube_token.json"
YOUTUBE_PROFILE_PATH = PROVIDERS_DIR / "youtube_profile.json"
YOUTUBE_OAUTH_STATE_PATH = PROVIDERS_DIR / "youtube_oauth_state.json"
