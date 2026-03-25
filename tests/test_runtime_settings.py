from __future__ import annotations

import os
from pathlib import Path

from clipmato.services.runtime_settings import RuntimeSettingsService


def test_runtime_settings_saved_values_override_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLIPMATO_CONTENT_BACKEND", "openai")
    monkeypatch.setenv("CLIPMATO_OLLAMA_BASE_URL", "http://env-ollama:11434")

    service = RuntimeSettingsService(
        settings_path=tmp_path / "settings.json",
        secrets_path=tmp_path / "secrets.json",
    )
    service.update_user_settings(
        {
            "content_backend": "ollama",
            "ollama_base_url": "http://saved-ollama:11434",
            "public_base_url": "https://clipmato.example.com/",
        }
    )

    resolved = service.resolve_settings()

    assert resolved["content_backend"] == "ollama"
    assert resolved["ollama_base_url"] == "http://saved-ollama:11434"
    assert resolved["public_base_url"] == "https://clipmato.example.com"
    assert resolved["settings_sources"]["content_backend"] == "saved"
    assert resolved["settings_sources"]["ollama_base_url"] == "saved"


def test_runtime_settings_secrets_prefer_saved_values_and_fall_back_to_env(monkeypatch, tmp_path: Path) -> None:
    service = RuntimeSettingsService(
        settings_path=tmp_path / "settings.json",
        secrets_path=tmp_path / "secrets.json",
    )
    service.update_secrets({"openai_api_key": "saved-openai-key"})

    assert service.get_secret("openai_api_key") == "saved-openai-key"
    assert service.secret_status("openai_api_key") == {"configured": True, "source": "saved"}

    service.delete_secret("openai_api_key")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    assert service.get_secret("openai_api_key") == "env-openai-key"
    assert service.secret_status("openai_api_key") == {"configured": True, "source": "env"}

    if os.name != "nt":
        mode = (tmp_path / "secrets.json").stat().st_mode & 0o777
        assert mode == 0o600


def test_apply_local_offline_profile_sets_whisper_and_ollama_defaults(tmp_path: Path) -> None:
    service = RuntimeSettingsService(
        settings_path=tmp_path / "settings.json",
        secrets_path=tmp_path / "secrets.json",
    )

    resolved = service.apply_runtime_profile("local-offline")

    assert resolved["transcription_backend"] == "local-whisper"
    assert resolved["content_backend"] == "ollama"
    assert resolved["ollama_model"] == "mistral-nemo:12b-instruct-2407-q3_K_S"
    assert resolved["ollama_timeout_seconds"] == 120
