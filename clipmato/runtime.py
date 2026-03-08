"""Runtime backend selection and environment status helpers."""
from __future__ import annotations

import importlib.util
import os


TRANSCRIPTION_BACKENDS = {"auto", "openai", "local-whisper"}
CONTENT_BACKENDS = {"auto", "openai", "local"}


def _normalized_env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    return value or default


def has_openai_api_key() -> bool:
    """Return whether an OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def local_whisper_installed() -> bool:
    """Return whether the optional local Whisper dependency is available."""
    return importlib.util.find_spec("whisper") is not None


def requested_transcription_backend() -> str:
    """Return the configured transcription backend."""
    backend = _normalized_env("CLIPMATO_TRANSCRIPTION_BACKEND", "auto")
    return backend if backend in TRANSCRIPTION_BACKENDS else "auto"


def requested_content_backend() -> str:
    """Return the configured content-generation backend."""
    backend = _normalized_env("CLIPMATO_CONTENT_BACKEND", "auto")
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
        return "openai" if has_openai_api_key() else "local"
    return backend


def detect_local_whisper_device() -> str:
    """
    Resolve the preferred local Whisper device.

    `mps` is used on Apple Silicon when available, `cuda` on NVIDIA systems,
    otherwise CPU.
    """
    configured = _normalized_env("CLIPMATO_LOCAL_WHISPER_DEVICE", "auto")
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
    transcription_backend = resolve_transcription_backend()
    content_backend = resolve_content_backend()
    blockers: list[str] = []
    warnings: list[str] = []

    if transcription_backend == "local-whisper" and not local_whisper_installed():
        blockers.append(
            "Local Whisper is selected for transcription, but the optional "
            "dependency is not installed. Install `pip install -e '.[local-transcription]'` "
            "for a host-native run, or switch to the OpenAI backend."
        )

    if transcription_backend == "openai" and not has_openai_api_key():
        blockers.append(
            "No OpenAI API key is configured for transcription. Set `OPENAI_API_KEY`, "
            "or install local Whisper and run with `CLIPMATO_TRANSCRIPTION_BACKEND=local-whisper`."
        )

    if content_backend == "local":
        warnings.append(
            "Descriptions, entities, titles, and script generation are using the local "
            "basic fallback backend to avoid API usage."
        )

    status = {
        "openai_api_key_configured": has_openai_api_key(),
        "requested_transcription_backend": requested_transcription_backend(),
        "transcription_backend": transcription_backend,
        "requested_content_backend": requested_content_backend(),
        "content_backend": content_backend,
        "local_whisper_installed": local_whisper_installed(),
        "local_whisper_device": detect_local_whisper_device(),
        "blockers": blockers,
        "warnings": warnings,
    }
    return status
