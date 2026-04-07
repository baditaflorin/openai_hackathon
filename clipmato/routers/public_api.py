"""Versioned public API routes."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..api.contracts import (
    ProgressStatusResponse,
    ProjectPresetListResponse,
    PublishJobUpdateResponse,
    RecordDetailModel,
    RecordListResponse,
    RuntimeStatusModel,
    ScheduleRecordRequest,
    TitleSelectionRequest,
    TitleUpdateResponse,
    UploadAcceptedResponse,
)
from ..api.errors import (
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_REPLAY_HEADER,
    ApiError,
    api_error_from_http_exception,
    error_responses,
)
from ..api.idempotency import fingerprint_payload, fingerprint_upload, idempotency_store
from ..dependencies import (
    get_file_io_service,
    get_metadata_service,
    get_processing_service,
    get_progress_service,
    get_project_preset_service,
    get_publishing_service,
    get_record_query_service,
)
from ..runtime import get_runtime_status
from ..utils import file_io as file_io_utils

router = APIRouter(prefix="/api/v1", tags=["Public API"])


def _model_dump(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return dict(payload)


def _idempotency_scope(path: str, key: str) -> str:
    return f"{path}:{key}"


def _idempotency_replay(path: str, key: str | None, fingerprint: str) -> JSONResponse | None:
    if not key:
        return None
    try:
        stored = idempotency_store.lookup(_idempotency_scope(path, key), fingerprint)
    except ValueError as exc:
        raise ApiError(
            status_code=409,
            code="idempotency_key_reused",
            message=str(exc),
        ) from exc
    if stored is None:
        return None
    return JSONResponse(
        status_code=stored.status_code,
        content=stored.body,
        headers={IDEMPOTENCY_REPLAY_HEADER: "true"},
    )


def _store_idempotent_response(
    path: str,
    key: str | None,
    fingerprint: str | None,
    body: dict[str, Any],
    status_code: int,
) -> None:
    if not key or not fingerprint:
        return
    idempotency_store.store_response(
        _idempotency_scope(path, key),
        fingerprint=fingerprint,
        status_code=status_code,
        body=jsonable_encoder(body),
    )


@router.get("/runtime/status", response_model=RuntimeStatusModel, responses=error_responses())
async def runtime_status() -> dict[str, Any]:
    """Return the resolved runtime configuration and blockers."""
    return get_runtime_status()


@router.get("/project-presets", response_model=ProjectPresetListResponse, responses=error_responses())
async def list_project_presets(project_preset_svc=Depends(get_project_preset_service)) -> dict[str, Any]:
    """Return the saved project presets available to API clients."""
    return {"project_presets": project_preset_svc.read()}


@router.get("/records", response_model=RecordListResponse, responses=error_responses())
async def list_records(
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    record_queries=Depends(get_record_query_service),
) -> dict[str, Any]:
    """List records using the versioned public summary contract."""
    records = record_queries.list_recent_records(metadata_svc, progress_svc)
    return {"records": [record_queries.build_summary_payload(record, detail_url_base="/api/v1/record") for record in records]}


@router.get("/record/{record_id}", response_model=RecordDetailModel, responses=error_responses())
async def get_record(
    record_id: str,
    metadata_svc=Depends(get_metadata_service),
    progress_svc=Depends(get_progress_service),
    record_queries=Depends(get_record_query_service),
) -> dict[str, Any]:
    """Return one record using the versioned public detail contract."""
    record = record_queries.get_record(metadata_svc, progress_svc, record_id)
    if record is None:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found")
    return record_queries.build_public_detail_payload(record)


@router.get("/progress/{record_id}", response_model=ProgressStatusResponse, responses=error_responses())
async def get_progress(
    record_id: str,
    progress_svc=Depends(get_progress_service),
) -> dict[str, Any]:
    """Return the current progress state for a record."""
    return progress_svc.read(record_id)


@router.post("/record/{record_id}/title", response_model=TitleUpdateResponse, responses=error_responses())
async def select_title(
    record_id: str,
    payload: TitleSelectionRequest,
    metadata_svc=Depends(get_metadata_service),
) -> dict[str, Any]:
    """Persist the selected title for a record."""
    updated = metadata_svc.update(record_id, {"selected_title": payload.selected_title})
    if updated is None:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found")
    return {"id": record_id, "selected_title": payload.selected_title}


@router.post("/record/{record_id}/schedule", response_model=PublishJobUpdateResponse, responses=error_responses())
async def schedule_record(
    record_id: str,
    payload: ScheduleRecordRequest,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    publishing_svc=Depends(get_publishing_service),
    metadata_svc=Depends(get_metadata_service),
) -> dict[str, Any] | JSONResponse:
    """Schedule a record and persist provider publish jobs."""
    if metadata_svc.get(record_id) is None:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found")

    payload_dict = _model_dump(payload)
    fingerprint = fingerprint_payload({"record_id": record_id, **payload_dict})
    replay = _idempotency_replay(f"/api/v1/record/{record_id}/schedule", idempotency_key, fingerprint)
    if replay is not None:
        return replay

    try:
        updated = publishing_svc.schedule_record(
            record_id,
            payload.schedule_time,
            payload.publish_targets,
            youtube_privacy_status=payload.youtube_privacy_status,
        )
    except KeyError as exc:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found") from exc

    body = {
        "id": record_id,
        "schedule_time": updated.get("schedule_time"),
        "publish_targets": list(updated.get("publish_targets") or []),
        "publish_jobs": dict(updated.get("publish_jobs") or {}),
    }
    _store_idempotent_response(
        f"/api/v1/record/{record_id}/schedule",
        idempotency_key,
        fingerprint,
        body,
        200,
    )
    return body


@router.post(
    "/record/{record_id}/publish/youtube/now",
    response_model=PublishJobUpdateResponse,
    responses=error_responses(),
)
async def publish_youtube_now(
    record_id: str,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    metadata_svc=Depends(get_metadata_service),
    publishing_svc=Depends(get_publishing_service),
) -> dict[str, Any] | JSONResponse:
    """Queue a record for immediate YouTube publishing."""
    if metadata_svc.get(record_id) is None:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found")

    fingerprint = fingerprint_payload({"record_id": record_id, "action": "publish_now", "provider": "youtube"})
    replay = _idempotency_replay(f"/api/v1/record/{record_id}/publish/youtube/now", idempotency_key, fingerprint)
    if replay is not None:
        return replay

    try:
        updated = publishing_svc.queue_publish_now(record_id)
    except KeyError as exc:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found") from exc
    except Exception as exc:
        message = str(exc) or "Failed to queue YouTube publish."
        raise ApiError(status_code=400, code="publish_request_failed", message=message) from exc

    body = {
        "id": record_id,
        "schedule_time": updated.get("schedule_time"),
        "publish_targets": list(updated.get("publish_targets") or []),
        "publish_jobs": dict(updated.get("publish_jobs") or {}),
    }
    _store_idempotent_response(
        f"/api/v1/record/{record_id}/publish/youtube/now",
        idempotency_key,
        fingerprint,
        body,
        200,
    )
    return body


@router.post(
    "/record/{record_id}/publish/youtube/retry",
    response_model=PublishJobUpdateResponse,
    responses=error_responses(),
)
async def retry_youtube_publish(
    record_id: str,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    metadata_svc=Depends(get_metadata_service),
    publishing_svc=Depends(get_publishing_service),
) -> dict[str, Any] | JSONResponse:
    """Retry a failed or blocked YouTube publish job."""
    if metadata_svc.get(record_id) is None:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found")

    fingerprint = fingerprint_payload({"record_id": record_id, "action": "retry_publish", "provider": "youtube"})
    replay = _idempotency_replay(f"/api/v1/record/{record_id}/publish/youtube/retry", idempotency_key, fingerprint)
    if replay is not None:
        return replay

    try:
        updated = publishing_svc.retry_record(record_id, "youtube")
    except KeyError as exc:
        raise ApiError(status_code=404, code="record_not_found", message="Record not found") from exc
    except Exception as exc:
        message = str(exc) or "Failed to retry YouTube publish."
        raise ApiError(status_code=400, code="publish_retry_failed", message=message) from exc

    body = {
        "id": record_id,
        "schedule_time": updated.get("schedule_time"),
        "publish_targets": list(updated.get("publish_targets") or []),
        "publish_jobs": dict(updated.get("publish_jobs") or {}),
    }
    _store_idempotent_response(
        f"/api/v1/record/{record_id}/publish/youtube/retry",
        idempotency_key,
        fingerprint,
        body,
        200,
    )
    return body


@router.post("/upload", response_model=UploadAcceptedResponse, responses=error_responses())
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
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    file_io=Depends(get_file_io_service),
    project_preset_svc=Depends(get_project_preset_service),
    processing_svc=Depends(get_processing_service),
    progress_svc=Depends(get_progress_service),
) -> dict[str, Any] | JSONResponse:
    """Accept an upload using the versioned public contract."""
    runtime_status = get_runtime_status()
    blockers = runtime_status.get("blockers", [])
    if blockers:
        raise ApiError(
            status_code=400,
            code="runtime_blocked",
            message=str(blockers[0]),
            details={"blockers": list(blockers)},
        )

    try:
        file_io_utils.validate_upload_file(file)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise api_error_from_http_exception(exc) from exc
        raise

    request_payload = {
        "remove_silence": remove_silence,
        "selected_project_presets": list(selected_project_presets),
        "project_name": project_name,
        "project_summary": project_summary,
        "project_topics": project_topics,
        "project_prompt_prefix": project_prompt_prefix,
        "project_prompt_suffix": project_prompt_suffix,
    }
    fingerprint = fingerprint_upload(file, request_payload) if idempotency_key else None
    if fingerprint is not None:
        replay = _idempotency_replay("/api/v1/upload", idempotency_key, fingerprint)
        if replay is not None:
            return replay

    try:
        file_path = file_io.save(file)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise api_error_from_http_exception(exc) from exc
        raise ApiError(
            status_code=500,
            code="upload_storage_failed",
            message="Failed to store uploaded file",
        ) from exc

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
    record_id = str(uuid4())
    if runtime_status["transcription_backend"] == "local-whisper":
        message = f"Local Whisper on {runtime_status['local_whisper_device']}"
    else:
        message = "OpenAI Whisper API"

    progress_svc.update(record_id, "transcribing", message)
    background_tasks.add_task(
        processing_svc.process,
        file_path,
        file.filename,
        record_id,
        remove_silence,
        merged_project_context,
    )
    body = {"id": record_id}
    _store_idempotent_response("/api/v1/upload", idempotency_key, fingerprint, body, 200)
    return body
