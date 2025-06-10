"""
Routes for viewing and managing individual episode records.
"""
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

from .common import read_metadata, update_metadata, remove_metadata, upload_dir, TEMPLATES

router = APIRouter()


@router.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(request: Request, record_id: str):
    """Show detailed view for a processed record."""
    records = read_metadata()
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return TEMPLATES.TemplateResponse("record.html", {"request": request, "record": record})


@router.post("/record/{record_id}/title", response_class=HTMLResponse)
async def select_title(request: Request, record_id: str, selected_title: str = Form(...)):
    """Handle the user selection of a title for a processed record."""
    records = read_metadata()
    record = next((it for it in records if it.get("id") == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    update_metadata(record_id, {"selected_title": selected_title})
    return RedirectResponse(url=f"/record/{record_id}", status_code=303)


@router.post("/record/{record_id}/delete")
async def delete_record(record_id: str):
    """Delete a processed record and its associated files."""
    rec = remove_metadata(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    src = upload_dir / rec.get("filename", "")
    if src.exists():
        try:
            src.unlink()
        except Exception:
            pass
    dst = Path(src).with_suffix('.wav')
    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass
    return RedirectResponse(url="/", status_code=303)