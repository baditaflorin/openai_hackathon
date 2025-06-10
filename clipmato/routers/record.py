"""
Routes for viewing and managing individual episode records.
"""
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

from ..dependencies import (
    get_templates,
    get_metadata_service,
    get_file_io_service,
)

router = APIRouter()


@router.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(
    request: Request,
    record_id: str,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
):
    """Show detailed view for a processed record."""
    records = metadata_svc.read()
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return templates.TemplateResponse(
        "record.html", {"request": request, "record": record}
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
    metadata_svc.update(record_id, {"selected_title": selected_title})
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
    return RedirectResponse(url="/", status_code=303)