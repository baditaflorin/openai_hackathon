"""Persistent runtime settings and credential storage."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import fcntl

from ..config import (
    CONTENT_BACKEND_ENV_VAR,
    GOOGLE_CLIENT_ID_ENV_VAR,
    GOOGLE_CLIENT_SECRET_ENV_VAR,
    LOCAL_WHISPER_DEVICE_ENV_VAR,
    LOCAL_WHISPER_MODEL_ENV_VAR,
    OLLAMA_BASE_URL_ENV_VAR,
    OLLAMA_MODEL_ENV_VAR,
    OLLAMA_TIMEOUT_ENV_VAR,
    OPENAI_API_KEY_ENV_VAR,
    OPENAI_CONTENT_MODEL_ENV_VAR,
    PUBLIC_BASE_URL_ENV_VAR,
    SECRETS_PATH,
    SETTINGS_PATH,
    TRANSCRIPTION_BACKEND_ENV_VAR,
)


TRANSCRIPTION_BACKEND_VALUES = {"auto", "openai", "local-whisper"}
CONTENT_BACKEND_VALUES = {"auto", "openai", "local-basic", "local", "ollama"}
LOCAL_WHISPER_DEVICE_VALUES = {"auto", "cpu", "cuda", "mps"}
SETTING_KEYS = (
    "transcription_backend",
    "content_backend",
    "local_whisper_model",
    "local_whisper_device",
    "ollama_base_url",
    "ollama_model",
    "ollama_timeout_seconds",
    "public_base_url",
    "openai_content_model",
)
SECRET_KEYS = (
    "openai_api_key",
    "google_client_id",
    "google_client_secret",
)
SECRET_ENV_MAP = {
    "openai_api_key": OPENAI_API_KEY_ENV_VAR,
    "google_client_id": GOOGLE_CLIENT_ID_ENV_VAR,
    "google_client_secret": GOOGLE_CLIENT_SECRET_ENV_VAR,
}
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OPENAI_CONTENT_MODEL = (
    os.getenv(OPENAI_CONTENT_MODEL_ENV_VAR, "").strip()
    or os.getenv("OPENAI_MODEL", "").strip()
    or "openai-agents-default"
)


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_url(value: Any) -> str:
    return _normalized_text(value).rstrip("/")


def _normalize_transcription_backend(value: Any) -> str:
    backend = _normalized_text(value).lower() or "auto"
    return backend if backend in TRANSCRIPTION_BACKEND_VALUES else "auto"


def _normalize_content_backend(value: Any) -> str:
    backend = _normalized_text(value).lower() or "auto"
    if backend == "local":
        backend = "local-basic"
    return backend if backend in CONTENT_BACKEND_VALUES else "auto"


def _normalize_local_whisper_device(value: Any) -> str:
    device = _normalized_text(value).lower() or "auto"
    return device if device in LOCAL_WHISPER_DEVICE_VALUES else "auto"


def _normalize_timeout(value: Any) -> int:
    try:
        return max(int(value), 5)
    except (TypeError, ValueError):
        return 60


def _runtime_defaults_from_env() -> tuple[dict[str, Any], dict[str, str]]:
    defaults = {
        "transcription_backend": _normalize_transcription_backend(os.getenv(TRANSCRIPTION_BACKEND_ENV_VAR, "auto")),
        "content_backend": _normalize_content_backend(os.getenv(CONTENT_BACKEND_ENV_VAR, "auto")),
        "local_whisper_model": _normalized_text(os.getenv(LOCAL_WHISPER_MODEL_ENV_VAR, "base")) or "base",
        "local_whisper_device": _normalize_local_whisper_device(os.getenv(LOCAL_WHISPER_DEVICE_ENV_VAR, "auto")),
        "ollama_base_url": _normalized_url(os.getenv(OLLAMA_BASE_URL_ENV_VAR, DEFAULT_OLLAMA_BASE_URL))
        or DEFAULT_OLLAMA_BASE_URL,
        "ollama_model": _normalized_text(os.getenv(OLLAMA_MODEL_ENV_VAR, DEFAULT_OLLAMA_MODEL)) or DEFAULT_OLLAMA_MODEL,
        "ollama_timeout_seconds": _normalize_timeout(os.getenv(OLLAMA_TIMEOUT_ENV_VAR, "60")),
        "public_base_url": _normalized_url(os.getenv(PUBLIC_BASE_URL_ENV_VAR, "")),
        "openai_content_model": _normalized_text(os.getenv(OPENAI_CONTENT_MODEL_ENV_VAR, DEFAULT_OPENAI_CONTENT_MODEL))
        or DEFAULT_OPENAI_CONTENT_MODEL,
    }
    sources = {
        "transcription_backend": "env" if TRANSCRIPTION_BACKEND_ENV_VAR in os.environ else "default",
        "content_backend": "env" if CONTENT_BACKEND_ENV_VAR in os.environ else "default",
        "local_whisper_model": "env" if LOCAL_WHISPER_MODEL_ENV_VAR in os.environ else "default",
        "local_whisper_device": "env" if LOCAL_WHISPER_DEVICE_ENV_VAR in os.environ else "default",
        "ollama_base_url": "env" if OLLAMA_BASE_URL_ENV_VAR in os.environ else "default",
        "ollama_model": "env" if OLLAMA_MODEL_ENV_VAR in os.environ else "default",
        "ollama_timeout_seconds": "env" if OLLAMA_TIMEOUT_ENV_VAR in os.environ else "default",
        "public_base_url": "env" if PUBLIC_BASE_URL_ENV_VAR in os.environ else "default",
        "openai_content_model": "env" if OPENAI_CONTENT_MODEL_ENV_VAR in os.environ else "default",
    }
    return defaults, sources


def _normalize_setting_value(key: str, value: Any) -> Any:
    if key == "transcription_backend":
        return _normalize_transcription_backend(value)
    if key == "content_backend":
        return _normalize_content_backend(value)
    if key == "local_whisper_model":
        return _normalized_text(value) or "base"
    if key == "local_whisper_device":
        return _normalize_local_whisper_device(value)
    if key == "ollama_base_url":
        return _normalized_url(value) or DEFAULT_OLLAMA_BASE_URL
    if key == "ollama_model":
        return _normalized_text(value) or DEFAULT_OLLAMA_MODEL
    if key == "ollama_timeout_seconds":
        return _normalize_timeout(value)
    if key == "public_base_url":
        return _normalized_url(value)
    if key == "openai_content_model":
        return _normalized_text(value) or DEFAULT_OPENAI_CONTENT_MODEL
    raise KeyError(key)


def _lock_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.lock")


@contextmanager
def _locked_file(path: Path):
    lock_path = _lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any], *, secret: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f"{path.stem}_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        if secret:
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class RuntimeSettingsService:
    """Read and write runtime preferences and stored credentials."""

    def __init__(self, settings_path: Path = SETTINGS_PATH, secrets_path: Path = SECRETS_PATH) -> None:
        self.settings_path = settings_path
        self.secrets_path = secrets_path

    def read_user_settings(self) -> dict[str, Any]:
        """Return persisted non-secret settings."""
        with _locked_file(self.settings_path):
            raw = _read_json(self.settings_path)
        return {
            key: _normalize_setting_value(key, raw[key])
            for key in SETTING_KEYS
            if key in raw and _normalized_text(raw[key]) != ""
        }

    def read_user_secrets(self, *, include_values: bool = False) -> dict[str, Any]:
        """Return persisted secret values or just status metadata."""
        with _locked_file(self.secrets_path):
            raw = _read_json(self.secrets_path)
        if include_values:
            return {key: _normalized_text(raw.get(key, "")) for key in SECRET_KEYS}
        return {
            key: {
                "configured": bool(_normalized_text(raw.get(key, ""))),
                "source": "saved" if _normalized_text(raw.get(key, "")) else "missing",
            }
            for key in SECRET_KEYS
        }

    def resolve_settings(self) -> dict[str, Any]:
        """Return resolved settings with source attribution."""
        defaults, default_sources = _runtime_defaults_from_env()
        saved = self.read_user_settings()
        resolved = dict(defaults)
        sources = dict(default_sources)
        for key, value in saved.items():
            resolved[key] = value
            sources[key] = "saved"
        resolved["settings_sources"] = sources
        return resolved

    def get_setting(self, key: str) -> Any:
        """Return one resolved setting value."""
        return self.resolve_settings()[key]

    def update_user_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Persist selected user settings and return the resolved settings."""
        with _locked_file(self.settings_path):
            current = _read_json(self.settings_path)
            for key, value in updates.items():
                if key not in SETTING_KEYS:
                    continue
                if value is None or _normalized_text(value) == "":
                    current.pop(key, None)
                    continue
                current[key] = _normalize_setting_value(key, value)
            _write_json(self.settings_path, current)
        return self.resolve_settings()

    def get_secret(self, key: str) -> str:
        """Return a secret from saved storage or environment fallback."""
        if key not in SECRET_KEYS:
            raise KeyError(key)
        with _locked_file(self.secrets_path):
            raw = _read_json(self.secrets_path)
        saved = _normalized_text(raw.get(key, ""))
        if saved:
            return saved
        env_name = SECRET_ENV_MAP[key]
        return _normalized_text(os.getenv(env_name, ""))

    def secret_status(self, key: str) -> dict[str, Any]:
        """Return whether a secret is configured and where it comes from."""
        if key not in SECRET_KEYS:
            raise KeyError(key)
        with _locked_file(self.secrets_path):
            raw = _read_json(self.secrets_path)
        saved = _normalized_text(raw.get(key, ""))
        if saved:
            return {"configured": True, "source": "saved"}
        env_name = SECRET_ENV_MAP[key]
        env_value = _normalized_text(os.getenv(env_name, ""))
        if env_value:
            return {"configured": True, "source": "env"}
        return {"configured": False, "source": "missing"}

    def update_secrets(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Persist secret values and return their statuses."""
        with _locked_file(self.secrets_path):
            current = _read_json(self.secrets_path)
            for key, value in updates.items():
                if key not in SECRET_KEYS:
                    continue
                normalized = _normalized_text(value)
                if normalized:
                    current[key] = normalized
                else:
                    current.pop(key, None)
            _write_json(self.secrets_path, current, secret=True)
        return {key: self.secret_status(key) for key in SECRET_KEYS}

    def delete_secret(self, key: str) -> None:
        """Delete a persisted secret value."""
        if key not in SECRET_KEYS:
            raise KeyError(key)
        with _locked_file(self.secrets_path):
            current = _read_json(self.secrets_path)
            current.pop(key, None)
            _write_json(self.secrets_path, current, secret=True)

    def summary(self) -> dict[str, Any]:
        """Return a UI-friendly combined settings summary."""
        resolved = self.resolve_settings()
        secrets = {key: self.secret_status(key) for key in SECRET_KEYS}
        return {
            **resolved,
            "secret_status": copy.deepcopy(secrets),
            "openai_api_key_configured": secrets["openai_api_key"]["configured"],
            "google_oauth_configured": (
                secrets["google_client_id"]["configured"] and secrets["google_client_secret"]["configured"]
            ),
        }
