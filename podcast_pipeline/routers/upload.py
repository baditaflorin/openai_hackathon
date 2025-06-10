"""
Routes for handling file uploads and rendering upload/index pages.
"""
from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse

from ..utils.file_io import save_upload_file
from ..services.file_processing import process_file_async
from ..utils.metadata import append_metadata, read_metadata
from ..config import TEMPLATES

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the upload form and list of processed files."""
    records = read_metadata()
    return TEMPLATES.TemplateResponse("index.html", {"request": request, "records": records})


@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    """Handle uploaded audio file and run through the processing pipeline."""
    file_path = save_upload_file(file)
    record = await process_file_async(file_path, file.filename)
    append_metadata(record)
    return TEMPLATES.TemplateResponse("result.html", {"request": request, **record})