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
    get_record_query_service,
)
from ..services.eventing import emit_event
from ..utils.presentation import workflow_metrics

router = APIRouter(include_in_schema=False)


@router.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(
    request: Request,
    record_id: str,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    record_queries=Depends(get_record_query_service),
):
    """Show detailed view for a processed record."""
    records = record_queries.list_recent_records(metadata_svc, progress_svc)
    record = record_queries.find_record(records, record_id)
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
    record_queries=Depends(get_record_query_service),
) -> JSONResponse:
    """Return a compact record payload for progressive frontend updates."""
    record = record_queries.get_record(metadata_svc, progress_svc, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse(record_queries.build_summary_payload(record, detail_url_base="/record"))


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
