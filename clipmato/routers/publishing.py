"""Routes for provider authorization and publish job controls."""
from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..dependencies import get_metadata_service, get_publishing_service
from ..providers import PublishError
from ..runtime import get_public_base_url

router = APIRouter()


def _scheduler_redirect(kind: str, message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/scheduler?{kind}={quote_plus(message)}", status_code=303)


def _public_callback_url(request: Request, route_name: str) -> str:
    public_base_url = get_public_base_url()
    if public_base_url:
        return f"{public_base_url}{request.app.url_path_for(route_name)}"
    return str(request.url_for(route_name))


@router.get("/auth/youtube/connect")
async def youtube_connect(
    request: Request,
    publishing_svc=Depends(get_publishing_service),
) -> RedirectResponse:
    """Start the YouTube OAuth flow."""
    try:
        authorization_url = publishing_svc.youtube.begin_authorization(
            _public_callback_url(request, "youtube_oauth_callback")
        )
    except PublishError as exc:
        return _scheduler_redirect("error", str(exc))
    return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/auth/youtube/callback", name="youtube_oauth_callback")
async def youtube_oauth_callback(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    publishing_svc=Depends(get_publishing_service),
) -> RedirectResponse:
    """Complete the YouTube OAuth callback and persist credentials."""
    if error:
        return _scheduler_redirect("error", f"YouTube authorization failed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback parameters")

    try:
        profile = publishing_svc.youtube.complete_authorization(
            _public_callback_url(request, "youtube_oauth_callback"),
            state=state,
            code=code,
        )
    except PublishError as exc:
        return _scheduler_redirect("error", str(exc))

    publishing_svc.refresh_all_jobs()
    channel_title = profile.get("channel_title") or "your account"
    return _scheduler_redirect("notice", f"YouTube connected for {channel_title}.")


@router.post("/auth/youtube/disconnect")
async def youtube_disconnect(
    publishing_svc=Depends(get_publishing_service),
) -> RedirectResponse:
    """Disconnect the stored YouTube account."""
    publishing_svc.youtube.disconnect()
    publishing_svc.refresh_all_jobs()
    return _scheduler_redirect("notice", "YouTube has been disconnected.")


@router.post("/record/{record_id}/publish/youtube/now")
async def publish_youtube_now(
    record_id: str,
    metadata_svc=Depends(get_metadata_service),
    publishing_svc=Depends(get_publishing_service),
) -> RedirectResponse:
    """Queue a record for the next publish worker tick."""
    if metadata_svc.get(record_id) is None:
        raise HTTPException(status_code=404, detail="Record not found")
    try:
        publishing_svc.queue_publish_now(record_id)
    except PublishError as exc:
        return _scheduler_redirect("error", str(exc))
    return _scheduler_redirect("notice", "YouTube publish queued.")


@router.post("/record/{record_id}/publish/youtube/retry")
async def retry_youtube_publish(
    record_id: str,
    metadata_svc=Depends(get_metadata_service),
    publishing_svc=Depends(get_publishing_service),
) -> RedirectResponse:
    """Retry a failed or blocked YouTube publish."""
    if metadata_svc.get(record_id) is None:
        raise HTTPException(status_code=404, detail="Record not found")
    try:
        publishing_svc.retry_record(record_id, "youtube")
    except (KeyError, PublishError) as exc:
        return _scheduler_redirect("error", str(exc))
    return _scheduler_redirect("notice", "YouTube publish requeued.")
