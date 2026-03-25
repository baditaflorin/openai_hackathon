"""
Routes for scheduling episodes, both manual and automatic.
"""
from urllib.parse import quote_plus

from fastapi import APIRouter, Request, HTTPException, Form, Depends
import calendar
import logging
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse

from ..agent_runs import AgentRunService, SchedulerAgentRunWorkflow
from ..config import YOUTUBE_DEFAULT_PRIVACY_STATUS
from ..dependencies import (
    get_agent_run_storage,
    get_templates,
    get_metadata_service,
    get_publishing_service,
    get_progress_service,
    get_scheduling_service,
)
from ..runtime import get_public_base_url
from ..utils.presentation import present_record, workflow_metrics

logger = logging.getLogger(__name__)

router = APIRouter()


def _youtube_callback_url(request: Request) -> str:
    public_base_url = get_public_base_url()
    if public_base_url:
        return f"{public_base_url}{request.app.url_path_for('youtube_oauth_callback')}"
    return str(request.url_for("youtube_oauth_callback"))


def _scheduler_redirect(kind: str, message: str, run_id: str | None = None) -> RedirectResponse:
    target = f"/scheduler?{kind}={quote_plus(message)}"
    if run_id:
        target = f"{target}&run_id={quote_plus(run_id)}"
    return RedirectResponse(url=target, status_code=303)


@router.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(
    request: Request,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    publishing_svc=Depends(get_publishing_service),
    agent_run_storage=Depends(get_agent_run_storage),
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
    run_reader = AgentRunService(storage=agent_run_storage)
    requested_run_id = request.query_params.get("run_id")
    scheduler_run = run_reader.get_run(requested_run_id) if requested_run_id else None
    if scheduler_run is None:
        latest_runs = run_reader.list_runs(workflow="scheduler_auto", limit=1)
        scheduler_run = latest_runs[0] if latest_runs else None
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
            "scheduler_run": scheduler_run,
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
    agent_run_storage=Depends(get_agent_run_storage),
    mode: str = Form("apply"),
):
    """Preview or apply schedule times through the persisted agent-run workflow."""
    logger.info(
        "Auto-scheduling request: cadence=%s, n_days=%s, mode=%s",
        cadence,
        n_days,
        mode,
    )
    live_apply = mode != "dry-run"
    workflow = SchedulerAgentRunWorkflow(
        metadata_svc=metadata_svc,
        scheduling_svc=scheduling_svc,
        publishing_svc=publishing_svc,
        storage=agent_run_storage,
    )
    run = await workflow.run(
        cadence=cadence,
        n_days=n_days,
        live_apply=live_apply,
        approval_granted=live_apply,
    )
    run_id = str(run["run_id"])
    if run["state"] == "failed":
        error = str((run.get("final_outcome") or {}).get("error") or "Scheduling agent run failed.")
        return _scheduler_redirect("error", error, run_id)
    if run["state"] == "awaiting_approval":
        return _scheduler_redirect(
            "notice",
            "Scheduling preview is ready and waiting for approval before live apply.",
            run_id,
        )
    if run.get("dry_run"):
        return _scheduler_redirect("notice", "Scheduling preview generated without changing any records.", run_id)
    applied_count = int((run.get("final_outcome") or {}).get("updated_record_ids") and len(run["final_outcome"]["updated_record_ids"]) or 0)
    return _scheduler_redirect(
        "notice",
        f"Scheduling agent applied updates to {applied_count} record(s).",
        run_id,
    )


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
