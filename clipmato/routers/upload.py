"""
Routes for handling file uploads and rendering upload/index pages.
"""
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse
from uuid import uuid4

from ..dependencies import (
    get_file_io_service,
    get_metadata_service,
    get_processing_service,
    get_progress_service,
    get_templates,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
):
    """Serve the upload form and list of processed files."""
    records = progress_svc.enrich(metadata_svc.read())
    return templates.TemplateResponse(
        "index.html", {"request": request, "records": records}
    )


@router.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    remove_silence: bool = Form(False),
    file_io=Depends(get_file_io_service),
    processing_svc=Depends(get_processing_service),
    progress_svc=Depends(get_progress_service),
) -> JSONResponse:
    """Handle uploaded file: save it, enqueue processing, and return a job ID."""
    try:
        file_path = file_io.save(file)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail="Failed to store uploaded file") from exc

    record_id = str(uuid4())
    # mark the pipeline as starting (after upload)
    progress_svc.update(record_id, "transcribing")
    # process the file in background (updates metadata and final status)
    background_tasks.add_task(
        processing_svc.process,
        file_path,
        file.filename,
        record_id,
        remove_silence,
    )
    return JSONResponse({"id": record_id})


@router.get("/progress/{record_id}")
async def progress(
    record_id: str,
    progress_svc=Depends(get_progress_service),
) -> JSONResponse:
    """Return the current progress status for a given job ID."""
    status = progress_svc.read(record_id)
    return JSONResponse(status)
