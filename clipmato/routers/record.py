"""
Routes for viewing and managing individual episode records.
"""
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pathlib import Path

from ..prompts import record_title_selection_evaluation
from ..config import YOUTUBE_DEFAULT_PRIVACY_STATUS
from ..dependencies import (
    get_templates,
    get_metadata_service,
    get_file_io_service,
    get_progress_service,
)
from ..services.eventing import emit_event
from ..utils.presentation import present_record, workflow_metrics

router = APIRouter(include_in_schema=False)


@router.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(
    request: Request,
    record_id: str,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
):
    """Show detailed view for a processed record."""
    records = [present_record(rec) for rec in progress_svc.enrich(metadata_svc.read())]
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return templates.TemplateResponse(
        request,
        "record.html",
        {
            "request": request,
            "record": record,
            "app_section": "library",
            "workflow_metrics": workflow_metrics(records),
            "default_youtube_privacy_status": YOUTUBE_DEFAULT_PRIVACY_STATUS,
        },
    )


@router.get("/record/{record_id}/summary")
async def record_summary(
    record_id: str,
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
) -> JSONResponse:
    """Return a compact record payload for progressive frontend updates."""
    records = [present_record(rec) for rec in progress_svc.enrich(metadata_svc.read())]
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse(
        {
            "id": record["id"],
            "filename": record.get("filename"),
            "display_title": record.get("display_title"),
            "display_title_helper": record.get("display_title_helper"),
            "upload_time": record.get("upload_time"),
            "progress": record.get("progress", 100),
            "stage": record.get("stage", "complete"),
            "message": record.get("message"),
            "error": record.get("error"),
            "schedule_time": record.get("schedule_time"),
            "youtube_job": record.get("youtube_job"),
            "detail_url": f"/record/{record_id}",
        }
    )


@router.post("/record/{record_id}/title", response_class=HTMLResponse)
async def select_title(
    record_id: str,
    selected_title: str = Form(...),
    metadata_svc=Depends(get_metadata_service),
):
    """Handle the user selection of a title for a processed record."""
    records = metadata_svc.read()
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    updated_record = metadata_svc.update(record_id, {"selected_title": selected_title})
    if updated_record is not None:
        record_title_selection_evaluation(updated_record, selected_title)
        try:
            emit_event(
                "record.title.selected",
                aggregate_id=record_id,
                record_id=record_id,
                payload={"selected_title": selected_title},
                correlation_id=record_id,
                source="record",
            )
        except Exception:
            pass
    return RedirectResponse(url=f"/record/{record_id}", status_code=303)


@router.post("/record/{record_id}/delete")
async def delete_record(
    record_id: str,
    metadata_svc=Depends(get_metadata_service),
    file_io=Depends(get_file_io_service),
):
    """Delete a processed record and its associated files."""
    rec = metadata_svc.remove(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    src = Path(file_io.upload_dir) / rec.get("filename", "")
    if src.exists():
        try:
            src.unlink()
        except Exception:
            pass
    dst = src.with_suffix('.wav')
    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass
    try:
        emit_event(
            "record.deleted",
            aggregate_id=record_id,
            record_id=record_id,
            payload={"filename": rec.get("filename")},
            correlation_id=record_id,
            source="record",
        )
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=303)
