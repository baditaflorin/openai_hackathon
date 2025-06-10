"""
Routes for handling file uploads and rendering upload/index pages.
"""
from fastapi import APIRouter, File, UploadFile, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from uuid import uuid4

from .common import (
    save_upload_file,
    process_file_async,
    read_metadata,
    update_progress,
    read_progress,
    enrich_with_progress,
    TEMPLATES,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the upload form and list of processed files."""
    records = enrich_with_progress(read_metadata())
    return TEMPLATES.TemplateResponse("index.html", {"request": request, "records": records})


@router.post("/upload")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    remove_silence: bool = Form(False),
) -> JSONResponse:
    """Handle uploaded file: save it, enqueue processing, and return a job ID."""
    file_path = save_upload_file(file)
    record_id = str(uuid4())
    # mark the pipeline as starting (after upload)
    update_progress(record_id, "transcribing")
    # process the file in background (updates metadata and final status)
    background_tasks.add_task(
        process_file_async,
        file_path,
        file.filename,
        record_id,
        remove_silence,
    )
    return JSONResponse({"id": record_id})


@router.get("/progress/{record_id}")
async def progress(request: Request, record_id: str) -> JSONResponse:
    """Return the current progress status for a given job ID."""
    status = read_progress(record_id)
    return JSONResponse(status)
