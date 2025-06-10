"""
Routes for scheduling episodes, both manual and automatic.
"""
from fastapi import APIRouter, Request, HTTPException, Form
import calendar
import logging
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse

from .common import read_metadata, update_metadata, propose_schedule_async, TEMPLATES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(request: Request):
    """Show the scheduling page for manual or automatic scheduling."""
    records = read_metadata()
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
    return TEMPLATES.TemplateResponse(
        "scheduler.html",
        {
            "request": request,
            "records": records,
            "calendar": cal,
            "month": month,
            "year": year,
            "month_name": calendar.month_name[month],
            "events": events,
        },
    )


@router.post("/scheduler/auto", response_class=RedirectResponse)
async def scheduler_auto(cadence: str = Form("daily"), n_days: int | None = Form(None)):
    """Automatically propose and save schedule times for unscheduled records."""
    logger.info(
        "Auto-scheduling request: cadence=%s, n_days=%s",
        cadence,
        n_days,
    )
    records = read_metadata()
    # schedule all unscheduled records (titles optional)
    unscheduled = [rec for rec in records if not rec.get("schedule_time")]
    if unscheduled:
        suggestions = await propose_schedule_async(unscheduled, cadence=cadence, n_days=n_days)
        for rid, stime in suggestions.items():
            update_metadata(rid, {"schedule_time": stime})
    return RedirectResponse(url="/scheduler", status_code=303)


@router.post("/record/{record_id}/schedule", response_class=RedirectResponse)
async def schedule_record(record_id: str,
                          schedule_time: str = Form(...),
                          publish_targets: list[str] = Form([])):
    """Handle manual scheduling and publish-target selection for a single record."""
    records = read_metadata()
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    update_metadata(record_id, {"schedule_time": schedule_time, "publish_targets": publish_targets})
    return RedirectResponse(url="/scheduler", status_code=303)