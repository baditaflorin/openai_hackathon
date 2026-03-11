"""Routes for runtime settings and credential management."""
from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import SECRETS_PATH, SETTINGS_PATH
from ..dependencies import (
    get_metadata_service,
    get_progress_service,
    get_publishing_service,
    get_runtime_settings_service,
    get_templates,
)
from ..runtime import get_public_base_url, get_runtime_status
from ..utils.presentation import present_record, workflow_metrics

router = APIRouter()

RUNTIME_SETTING_FIELDS = (
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


def _settings_redirect(kind: str, message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/settings?{kind}={quote_plus(message)}", status_code=303)


def _public_callback_url(request: Request) -> str:
    public_base_url = get_public_base_url()
    if public_base_url:
        return f"{public_base_url}{request.app.url_path_for('youtube_oauth_callback')}"
    return str(request.url_for("youtube_oauth_callback"))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    settings_svc=Depends(get_runtime_settings_service),
    publishing_svc=Depends(get_publishing_service),
):
    """Render the runtime settings and credential management page."""
    records = [present_record(rec) for rec in progress_svc.enrich(metadata_svc.read())]
    records.sort(key=lambda rec: rec.get("upload_time", ""), reverse=True)
    youtube_status = publishing_svc.get_provider_status(
        "youtube",
        redirect_uri=_public_callback_url(request),
    )
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "request": request,
            "settings_summary": settings_svc.summary(),
            "runtime_status": get_runtime_status(),
            "youtube_status": youtube_status,
            "settings_notice": request.query_params.get("notice"),
            "settings_error": request.query_params.get("error"),
            "settings_path": str(SETTINGS_PATH),
            "secrets_path": str(SECRETS_PATH),
            "app_section": "settings",
            "workflow_metrics": workflow_metrics(records),
        },
    )


@router.post("/settings/runtime")
async def save_runtime_settings(
    request: Request,
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Persist non-secret runtime preferences."""
    form = await request.form()
    updates = {field: form.get(field) for field in RUNTIME_SETTING_FIELDS}
    settings_svc.update_user_settings(updates)
    return _settings_redirect("notice", "Runtime settings saved.")


@router.post("/settings/runtime/profile/{profile}")
async def apply_runtime_profile(
    profile: str,
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Apply a named runtime profile for quick local/cloud switching."""
    try:
        settings_svc.apply_runtime_profile(profile)
    except ValueError as exc:
        return _settings_redirect("error", str(exc))
    if profile == "local-offline":
        return _settings_redirect(
            "notice",
            "Local offline profile applied: local Whisper + Ollama mistral-nemo:12b-instruct-2407-q3_K_S.",
        )
    if profile == "apple-host-ollama":
        return _settings_redirect(
            "notice",
            "Apple host Ollama profile applied: local Whisper on mps + host-native Ollama at http://host.docker.internal:11434 using Mistral NeMo.",
        )
    if profile == "gpt-oss-high-memory":
        return _settings_redirect("notice", "High-memory Ollama profile applied: gpt-oss:20b.")
    if profile == "openai-cloud":
        return _settings_redirect("notice", "OpenAI cloud profile applied.")
    return _settings_redirect("notice", "Runtime profile applied.")


@router.post("/settings/credentials/openai")
async def save_openai_credentials(
    request: Request,
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Persist a saved OpenAI API key."""
    form = await request.form()
    openai_api_key = str(form.get("openai_api_key", "")).strip()
    if not openai_api_key:
        return _settings_redirect("error", "Enter an OpenAI API key to save, or use delete to clear the saved one.")
    settings_svc.update_secrets({"openai_api_key": openai_api_key})
    return _settings_redirect("notice", "OpenAI API key saved.")


@router.post("/settings/credentials/openai/delete")
async def delete_openai_credentials(
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Delete the saved OpenAI API key."""
    settings_svc.delete_secret("openai_api_key")
    return _settings_redirect("notice", "Saved OpenAI API key removed.")


@router.post("/settings/credentials/google")
async def save_google_credentials(
    request: Request,
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Persist Google OAuth client credentials."""
    form = await request.form()
    updates: dict[str, str] = {}
    google_client_id = str(form.get("google_client_id", "")).strip()
    google_client_secret = str(form.get("google_client_secret", "")).strip()
    if google_client_id:
        updates["google_client_id"] = google_client_id
    if google_client_secret:
        updates["google_client_secret"] = google_client_secret
    if not updates:
        return _settings_redirect(
            "error",
            "Enter a Google client ID or client secret to save, or use delete to clear the saved ones.",
        )
    settings_svc.update_secrets(updates)
    return _settings_redirect("notice", "Google OAuth credentials saved.")


@router.post("/settings/credentials/google/delete")
async def delete_google_credentials(
    settings_svc=Depends(get_runtime_settings_service),
) -> RedirectResponse:
    """Delete the saved Google OAuth client credentials."""
    settings_svc.delete_secret("google_client_id")
    settings_svc.delete_secret("google_client_secret")
    return _settings_redirect("notice", "Saved Google OAuth credentials removed.")
