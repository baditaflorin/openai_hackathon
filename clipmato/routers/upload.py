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
    get_project_preset_service,
    get_processing_service,
    get_progress_service,
    get_templates,
)
from ..services.eventing import emit_event
from ..runtime import get_runtime_status
from ..utils.presentation import present_record, workflow_metrics

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    templates=Depends(get_templates),
    metadata_svc=Depends(get_metadata_service),
    project_preset_svc=Depends(get_project_preset_service),
    progress_svc=Depends(get_progress_service),
):
    """Serve the upload form and list of processed files."""
    records = [present_record(rec) for rec in progress_svc.enrich(metadata_svc.read())]
    records.sort(key=lambda rec: rec.get("upload_time", ""), reverse=True)
    runtime_status = get_runtime_status()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "records": records,
            "project_presets": project_preset_svc.read(),
            "runtime_status": runtime_status,
            "app_section": "capture",
            "workflow_metrics": workflow_metrics(records),
        },
    )


@router.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    remove_silence: bool = Form(False),
    selected_project_presets: list[str] = Form(default=[]),
    project_name: str = Form(""),
    project_summary: str = Form(""),
    project_topics: str = Form(""),
    project_prompt_prefix: str = Form(""),
    project_prompt_suffix: str = Form(""),
    file_io=Depends(get_file_io_service),
    project_preset_svc=Depends(get_project_preset_service),
    processing_svc=Depends(get_processing_service),
    progress_svc=Depends(get_progress_service),
) -> JSONResponse:
    """Handle uploaded file: save it, enqueue processing, and return a job ID."""
    runtime_status = get_runtime_status()
    blockers = runtime_status.get("blockers", [])
    if blockers:
        return JSONResponse({"detail": blockers[0]}, status_code=400)

    try:
        file_path = file_io.save(file)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail="Failed to store uploaded file") from exc

    record_id = str(uuid4())
    if runtime_status["transcription_backend"] == "local-whisper":
        device = runtime_status["local_whisper_device"]
        message = f"Local Whisper on {device}"
    else:
        message = "OpenAI Whisper API"
    merged_project_context = project_preset_svc.merge_context(
        selected_project_presets,
        {
            "project_name": project_name,
            "project_summary": project_summary,
            "project_topics": project_topics,
            "project_prompt_prefix": project_prompt_prefix,
            "project_prompt_suffix": project_prompt_suffix,
        },
    )
    progress_svc.update(record_id, "transcribing", message)
    try:
        emit_event(
            "record.uploaded",
            aggregate_id=record_id,
            record_id=record_id,
            payload={
                "filename": file.filename,
                "remove_silence": remove_silence,
                "selected_project_presets": selected_project_presets,
            },
            correlation_id=record_id,
            source="upload",
        )
    except Exception:
        pass
    background_tasks.add_task(
        processing_svc.process,
        file_path,
        file.filename,
        record_id,
        remove_silence,
        merged_project_context,
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
