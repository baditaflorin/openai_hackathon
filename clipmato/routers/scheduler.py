"""
Routes for scheduling episodes, both manual and automatic.
"""
from fastapi import APIRouter, Request, HTTPException, Form, Depends
import calendar
import logging
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import PUBLIC_BASE_URL, YOUTUBE_DEFAULT_PRIVACY_STATUS
from ..dependencies import (
    get_templates,
    get_metadata_service,
    get_publishing_service,
    get_progress_service,
    get_scheduling_service,
)
from ..utils.presentation import present_record, workflow_metrics

logger = logging.getLogger(__name__)

router = APIRouter()


def _youtube_callback_url(request: Request) -> str:
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}{request.app.url_path_for('youtube_oauth_callback')}"
    return str(request.url_for("youtube_oauth_callback"))


@router.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(
    request: Request,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    publishing_svc=Depends(get_publishing_service),
):
    """Show the scheduling page for manual or automatic scheduling."""
    records = [present_record(rec) for rec in progress_svc.enrich(metadata_svc.read())]
    records.sort(key=lambda rec: rec.get("schedule_time") or rec.get("upload_time", ""))
    youtube_status = publishing_svc.get_provider_status(
        "youtube",
        redirect_uri=_youtube_callback_url(request),
    )
    today = datetime.today()
    year = today.year
    month = today.month
    cal = calendar.monthcalendar(year, month)
    events: list[dict] = []
    for rec in records:
        st = rec.get("schedule_time")
        if st:
            dt = datetime.fromisoformat(st)
            if dt.year == year and dt.month == month:
                events.append({
                    "day": dt.day,
                    "time": dt.strftime("%I:%M %p"),
                    "title": rec.get("selected_title") or rec.get("filename", ""),
                })
    return templates.TemplateResponse(
        request,
        "scheduler.html",
        {
            "request": request,
            "records": records,
            "calendar": cal,
            "month": month,
            "year": year,
            "month_name": calendar.month_name[month],
            "events": events,
            "youtube_status": youtube_status,
            "scheduler_notice": request.query_params.get("notice"),
            "scheduler_error": request.query_params.get("error"),
            "default_youtube_privacy_status": YOUTUBE_DEFAULT_PRIVACY_STATUS,
            "app_section": "schedule",
            "workflow_metrics": workflow_metrics(records),
        },
    )


@router.post("/scheduler/auto", response_class=RedirectResponse)
async def scheduler_auto(
    cadence: str = Form("daily"),
    n_days: int | None = Form(None),
    metadata_svc=Depends(get_metadata_service),
    scheduling_svc=Depends(get_scheduling_service),
    publishing_svc=Depends(get_publishing_service),
):
    """Automatically propose and save schedule times for unscheduled records."""
    logger.info(
        "Auto-scheduling request: cadence=%s, n_days=%s",
        cadence,
        n_days,
    )
    records = metadata_svc.read()
    # schedule all unscheduled records (titles optional)
    unscheduled = [rec for rec in records if not rec.get("schedule_time")]
    if unscheduled:
        suggestions = await scheduling_svc.propose(unscheduled, cadence=cadence, n_days=n_days)
        for rid, stime in suggestions.items():
            record = metadata_svc.get(rid)
            if record is None:
                continue
            publishing_svc.schedule_record(
                rid,
                stime,
                list(record.get("publish_targets") or []),
                youtube_privacy_status=((record.get("publish_jobs") or {}).get("youtube") or {}).get("privacy_status"),
            )
    return RedirectResponse(url="/scheduler", status_code=303)


@router.post("/record/{record_id}/schedule", response_class=RedirectResponse)
async def schedule_record(
    record_id: str,
    schedule_time: str = Form(...),
    publish_targets: list[str] = Form([]),
    youtube_privacy_status: str = Form(YOUTUBE_DEFAULT_PRIVACY_STATUS),
    metadata_svc=Depends(get_metadata_service),
    publishing_svc=Depends(get_publishing_service),
):
    """Handle manual scheduling and publish-target selection for a single record."""
    record = metadata_svc.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    publishing_svc.schedule_record(
        record_id,
        schedule_time,
        publish_targets,
        youtube_privacy_status=youtube_privacy_status,
    )
    return RedirectResponse(url="/scheduler", status_code=303)
