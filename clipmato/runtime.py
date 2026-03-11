"""Runtime backend selection and environment status helpers."""
from __future__ import annotations

import importlib.util
import logging
import os

import httpx

from .services.runtime_settings import RuntimeSettingsService


TRANSCRIPTION_BACKENDS = {"auto", "openai", "local-whisper"}
CONTENT_BACKENDS = {"auto", "openai", "local-basic", "ollama"}
_settings_service = RuntimeSettingsService()
logger = logging.getLogger(__name__)


def running_in_container() -> bool:
    """Return whether the current process appears to run inside a container."""
    return os.path.exists("/.dockerenv")


def get_runtime_preferences() -> dict[str, object]:
    """Return resolved runtime preferences."""
    return _settings_service.resolve_settings()


def get_public_base_url() -> str:
    """Return the resolved public base URL for callback generation."""
    return str(get_runtime_preferences()["public_base_url"])


def get_openai_api_key() -> str:
    """Return the effective OpenAI API key from saved secrets or env."""
    return _settings_service.get_secret("openai_api_key")


def has_openai_api_key() -> bool:
    """Return whether an OpenAI API key is configured."""
    return bool(get_openai_api_key())


def get_google_oauth_client_id() -> str:
    """Return the effective Google OAuth client ID."""
    return _settings_service.get_secret("google_client_id")


def get_google_oauth_client_secret() -> str:
    """Return the effective Google OAuth client secret."""
    return _settings_service.get_secret("google_client_secret")


def has_google_oauth_credentials() -> bool:
    """Return whether Google OAuth credentials are configured."""
    return bool(get_google_oauth_client_id() and get_google_oauth_client_secret())


def get_openai_content_model() -> str:
    """Return the resolved OpenAI content model name."""
    return str(get_runtime_preferences()["openai_content_model"])


def get_local_whisper_model() -> str:
    """Return the resolved local Whisper model name."""
    return str(get_runtime_preferences()["local_whisper_model"])


def get_ollama_base_url() -> str:
    """Return the resolved Ollama base URL."""
    return str(get_runtime_preferences()["ollama_base_url"])


def get_ollama_model() -> str:
    """Return the resolved Ollama model name."""
    return str(get_runtime_preferences()["ollama_model"])


def get_ollama_timeout_seconds() -> int:
    """Return the resolved Ollama timeout in seconds."""
    return int(get_runtime_preferences()["ollama_timeout_seconds"])


def ollama_reachable() -> bool:
    """Return whether the configured Ollama endpoint responds locally."""
    base_url = get_ollama_base_url()
    if not base_url:
        return False
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=min(get_ollama_timeout_seconds(), 2))
        response.raise_for_status()
    except Exception:
        logger.debug("Ollama endpoint is not reachable at %s", base_url, exc_info=True)
        return False
    return True


def local_whisper_installed() -> bool:
    """Return whether the optional local Whisper dependency is available."""
    return importlib.util.find_spec("whisper") is not None


def requested_transcription_backend() -> str:
    """Return the configured transcription backend."""
    backend = str(get_runtime_preferences()["transcription_backend"]).lower()
    return backend if backend in TRANSCRIPTION_BACKENDS else "auto"


def requested_content_backend() -> str:
    """Return the configured content-generation backend."""
    backend = str(get_runtime_preferences()["content_backend"]).lower()
    if backend == "local":
        backend = "local-basic"
    return backend if backend in CONTENT_BACKENDS else "auto"


def resolve_transcription_backend() -> str:
    """Resolve the effective transcription backend for this process."""
    backend = requested_transcription_backend()
    if backend == "auto":
        if has_openai_api_key():
            return "openai"
        if local_whisper_installed():
            return "local-whisper"
        return "openai"
    return backend


def resolve_content_backend() -> str:
    """Resolve the effective content-generation backend for this process."""
    backend = requested_content_backend()
    if backend == "auto":
        return "openai" if has_openai_api_key() else "local-basic"
    return backend


def detect_local_whisper_device() -> str:
    """
    Resolve the preferred local Whisper device.

    `mps` is used on Apple Silicon when available, `cuda` on NVIDIA systems,
    otherwise CPU.
    """
    configured = str(get_runtime_preferences()["local_whisper_device"]).lower()
    if configured != "auto":
        return configured

    try:
        import torch
    except Exception:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps and mps.is_available():
        return "mps"
    return "cpu"


def get_runtime_status() -> dict[str, object]:
    """Return a user-facing runtime status summary for the web UI."""
    preferences = get_runtime_preferences()
    transcription_backend = resolve_transcription_backend()
    content_backend = resolve_content_backend()
    local_whisper_device = detect_local_whisper_device()
    blockers: list[str] = []
    warnings: list[str] = []

    if transcription_backend == "local-whisper" and not local_whisper_installed():
        blockers.append(
            "Local Whisper is selected for transcription, but the optional "
            "dependency is not installed. Install `pip install -e '.[local-transcription]'` "
            "for a host-native run, or switch to the OpenAI backend."
        )
    if transcription_backend == "local-whisper" and running_in_container() and local_whisper_device != "cuda":
        warnings.append(
            "Clipmato is running inside Docker, so local Whisper cannot use Apple Metal (`mps`). "
            "In this setup Whisper will run on CPU. For Apple GPU transcription, run `clipmato-web` directly on macOS."
        )

    if transcription_backend == "openai" and not has_openai_api_key():
        blockers.append(
            "No OpenAI API key is configured for transcription. Save one in Settings, "
            "or install local Whisper and switch transcription to `local-whisper`."
        )

    if content_backend == "openai" and not has_openai_api_key():
        blockers.append(
            "OpenAI content generation is selected, but no OpenAI API key is configured. "
            "Save a key in Settings or switch content generation to `local-basic` or `ollama`."
        )

    if content_backend == "ollama" and (not get_ollama_base_url() or not get_ollama_model()):
        blockers.append(
            "Ollama content generation is selected, but the Ollama base URL or model is missing. "
            "Update the runtime settings before processing uploads."
        )
    if content_backend == "ollama" and not ollama_reachable():
        blockers.append(
            "Ollama content generation is selected, but the configured Ollama server is not reachable. "
            "Start Ollama locally and pull the selected model before running offline."
        )

    if content_backend == "local-basic":
        warnings.append(
            "Descriptions, entities, titles, and script generation are using the local "
            "basic fallback backend to avoid API usage."
        )

    if content_backend == "ollama":
        warnings.append(
            f"Content generation is routed to Ollama at {get_ollama_base_url()} using `{get_ollama_model()}`."
        )
        if get_ollama_base_url().startswith("http://ollama:"):
            warnings.append(
                "The Compose-managed Ollama service runs in Linux and will not use Apple Metal. "
                "For Apple GPU acceleration, run Ollama on macOS and point Clipmato at `http://host.docker.internal:11434`."
            )
        if get_ollama_model() == "gpt-oss:20b":
            warnings.append(
                "`gpt-oss:20b` is a high-memory model. If generation keeps falling back, switch to a smaller Ollama target like `mistral-nemo:12b-instruct-2407-q3_K_S` on 8 GB-class Macs."
            )
    if transcription_backend == "local-whisper":
        warnings.append(
            f"Transcription is configured for local Whisper using `{get_local_whisper_model()}` on `{local_whisper_device}`."
        )

    secret_status = {
        "openai_api_key": _settings_service.secret_status("openai_api_key"),
        "google_client_id": _settings_service.secret_status("google_client_id"),
        "google_client_secret": _settings_service.secret_status("google_client_secret"),
    }
    status = {
        "openai_api_key_configured": has_openai_api_key(),
        "google_oauth_configured": has_google_oauth_credentials(),
        "requested_transcription_backend": requested_transcription_backend(),
        "transcription_backend": transcription_backend,
        "requested_content_backend": requested_content_backend(),
        "content_backend": content_backend,
        "local_whisper_installed": local_whisper_installed(),
        "local_whisper_model": get_local_whisper_model(),
        "local_whisper_device": local_whisper_device,
        "running_in_container": running_in_container(),
        "openai_content_model": get_openai_content_model(),
        "ollama_base_url": get_ollama_base_url(),
        "ollama_model": get_ollama_model(),
        "ollama_timeout_seconds": get_ollama_timeout_seconds(),
        "ollama_reachable": ollama_reachable(),
        "public_base_url": get_public_base_url(),
        "settings_sources": preferences.get("settings_sources", {}),
        "secret_status": secret_status,
        "blockers": blockers,
        "warnings": warnings,
    }
    return status
