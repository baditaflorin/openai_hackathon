"""Versioned public API contracts, event streaming, and MCP gateway routes."""
from __future__ import annotations

import asyncio
import copy
import json
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from queue import Empty
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from ..api_support import api_error_response, api_success
from ..dependencies import (
    get_metadata_service,
    get_progress_service,
    publishing_service,
    runtime_settings_service,
)
from ..prompts import read_prompt_runs
from ..runtime import get_runtime_status
from ..services.event_log import EventLogService
from ..services.mcp_gateway import DRY_RUN_MODE, LIVE_APPLY_MODE, MCPGatewayService, ToolDefinition, ToolInvocation
from ..services.runtime_settings import RuntimeSettingsService
from ..utils.metadata import metadata_cache
from ..utils.presentation import present_record
from ..utils.static_assets import build_static_assets

router = APIRouter(prefix="/api/v1", tags=["api-v1"])

event_log_service = EventLogService()


class _SimpleRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = [stamp for stamp in self._hits[client_id] if stamp >= window_start]
        allowed = len(hits) < self.max_requests
        if allowed:
            hits.append(now)
        self._hits[client_id] = hits
        return allowed


class _IdempotencyStore:
    def __init__(self) -> None:
        self._results: dict[tuple[str, str, str], tuple[int, dict[str, Any], dict[str, Any]]] = {}

    def get(self, client_id: str, operation: str, key: str) -> tuple[int, dict[str, Any], dict[str, Any]] | None:
        return copy.deepcopy(self._results.get((client_id, operation, key)))

    def put(
        self,
        client_id: str,
        operation: str,
        key: str,
        response: tuple[int, dict[str, Any], dict[str, Any]],
    ) -> None:
        self._results[(client_id, operation, key)] = copy.deepcopy(response)


rate_limiter = _SimpleRateLimiter(max_requests=60, window_seconds=60)
idempotency_store = _IdempotencyStore()


class RuntimeLiveApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcription_backend: str | None = None
    content_backend: str | None = None
    local_whisper_model: str | None = None
    local_whisper_device: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    ollama_timeout_seconds: int | None = Field(default=None, ge=5)
    public_base_url: str | None = None
    openai_content_model: str | None = None


class MCPToolInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["dry_run", "live_apply", "dry-run", "preview", "apply", "live"] = "dry_run"
    approved: bool = False
    approval_token: str = ""
    scopes: list[str] = Field(default_factory=list)
    run_id: str | None = None
    actor: str = "api"


def _client_id(explicit_header: str | None) -> str:
    return (explicit_header or "").strip() or "anonymous"


def _preview_runtime_settings(updates: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        service = RuntimeSettingsService(
            settings_path=Path(tempdir) / "settings.json",
            secrets_path=Path(tempdir) / "secrets.json",
        )
        existing = runtime_settings_service.read_user_settings()
        if existing:
            service.update_user_settings(existing)
        return service.update_user_settings(updates)


def _preview_runtime_profile(profile: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        service = RuntimeSettingsService(
            settings_path=Path(tempdir) / "settings.json",
            secrets_path=Path(tempdir) / "secrets.json",
        )
        existing = runtime_settings_service.read_user_settings()
        if existing:
            service.update_user_settings(existing)
        return service.apply_runtime_profile(profile)


def _records_summary(limit: int | None = None) -> dict[str, Any]:
    records = [present_record(rec) for rec in get_progress_service().enrich(get_metadata_service().read())]
    records.sort(key=lambda rec: rec.get("upload_time", ""), reverse=True)
    visible = records[:limit] if limit is not None else records
    published = 0
    failed = 0
    scheduled = 0
    for record in visible:
        status = ((record.get("publish_jobs") or {}).get("youtube") or {}).get("status")
        if status == "published":
            published += 1
        elif status in {"failed", "blocked"}:
            failed += 1
        elif status:
            scheduled += 1
    return {
        "count": len(records),
        "visible_count": len(visible),
        "published_count": published,
        "failed_count": failed,
        "scheduled_count": scheduled,
        "records": visible,
    }


def _prompt_run_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    record_id = str(arguments.get("record_id", "") or "").strip() or None
    task = str(arguments.get("task", "") or "").strip() or None
    limit = int(arguments.get("limit", 10) or 10)
    runs = read_prompt_runs(record_id=record_id, task=task)
    runs.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return {
        "count": len(runs),
        "runs": runs[:limit],
    }


def _publish_status_summary() -> dict[str, Any]:
    records = get_metadata_service().read()
    jobs: list[dict[str, Any]] = []
    for record in records:
        youtube_job = (record.get("publish_jobs") or {}).get("youtube")
        if youtube_job:
            jobs.append(
                {
                    "record_id": record.get("id"),
                    "selected_title": record.get("selected_title"),
                    "status": youtube_job.get("status"),
                    "scheduled_for": youtube_job.get("scheduled_for"),
                    "remote_url": youtube_job.get("remote_url"),
                }
            )
    return {
        "provider_status": publishing_service.get_provider_status("youtube", redirect_uri=None),
        "jobs": jobs,
    }


def _resource_provider(definition, arguments: dict[str, Any]) -> dict[str, Any]:
    if definition.name == "runtime.summary":
        return {
            "settings_summary": runtime_settings_service.summary(),
            "runtime_status": get_runtime_status(),
        }
    if definition.name == "records.summary":
        limit = arguments.get("limit")
        return _records_summary(int(limit) if limit is not None else None)
    if definition.name == "prompt.run_metadata":
        return _prompt_run_summary(arguments)
    if definition.name == "publish.status":
        return _publish_status_summary()
    return {"resource": definition.name, "message": "No provider configured."}


def _approval_checker(invocation: ToolInvocation, definition: ToolDefinition) -> bool:
    return invocation.approval_token == "approved"


def _tool_executor(invocation: ToolInvocation, definition: ToolDefinition) -> dict[str, Any]:
    if definition.name == "runtime.settings.read":
        return {
            "settings_summary": runtime_settings_service.summary(),
            "runtime_status": get_runtime_status(),
        }
    if definition.name == "runtime.settings.update":
        updates = dict(invocation.arguments.get("updates") or {})
        if invocation.mode == DRY_RUN_MODE:
            return {
                "applied": False,
                "preview": True,
                "resolved_settings": _preview_runtime_settings(updates),
            }
        resolved = runtime_settings_service.update_user_settings(updates)
        event_log_service.emit(
            aggregate_id="runtime-settings",
            type="runtime.settings.updated",
            payload={"updates": updates, "resolved_settings": resolved},
            correlation_id=invocation.correlation_id or None,
            scopes=["runtime"],
            tags=["runtime", "settings", "live_apply"],
        )
        return {
            "applied": True,
            "resolved_settings": resolved,
            "settings_summary": runtime_settings_service.summary(),
            "runtime_status": get_runtime_status(),
        }
    if definition.name == "runtime.profile.apply":
        profile = str(invocation.arguments.get("profile", "")).strip()
        if invocation.mode == DRY_RUN_MODE:
            return {
                "applied": False,
                "preview": True,
                "profile": profile,
                "resolved_settings": _preview_runtime_profile(profile),
            }
        resolved = runtime_settings_service.apply_runtime_profile(profile)
        event_log_service.emit(
            aggregate_id="runtime-settings",
            type="runtime.profile.applied",
            payload={"profile": profile, "resolved_settings": resolved},
            correlation_id=invocation.correlation_id or None,
            scopes=["runtime"],
            tags=["runtime", "profile", "live_apply"],
        )
        return {
            "applied": True,
            "profile": profile,
            "resolved_settings": resolved,
            "settings_summary": runtime_settings_service.summary(),
            "runtime_status": get_runtime_status(),
        }
    if definition.name == "credentials.update":
        updates = dict(invocation.arguments.get("updates") or {})
        if invocation.mode == DRY_RUN_MODE:
            return {
                "applied": False,
                "preview": True,
                "keys": sorted(updates),
            }
        statuses = runtime_settings_service.update_secrets(updates)
        event_log_service.emit(
            aggregate_id="runtime-secrets",
            type="runtime.credentials.updated",
            payload={"keys": sorted(updates)},
            correlation_id=invocation.correlation_id or None,
            scopes=["credentials"],
            tags=["credentials", "live_apply"],
        )
        return {"applied": True, "secret_status": statuses}
    if definition.name == "admin.refresh":
        if invocation.mode == DRY_RUN_MODE:
            return {"applied": False, "preview": True, "actions": ["metadata_cache.warm", "build_static_assets"]}
        metadata_cache.warm()
        build_static_assets()
        event_log_service.emit(
            aggregate_id="admin",
            type="admin.refresh.completed",
            payload={"actions": ["metadata_cache.warm", "build_static_assets"]},
            correlation_id=invocation.correlation_id or None,
            scopes=["admin"],
            tags=["admin", "refresh"],
        )
        return {"applied": True, "actions": ["metadata_cache.warm", "build_static_assets"]}
    if definition.name == "publish.record":
        record_id = str(invocation.arguments.get("record_id", "")).strip()
        if invocation.mode == DRY_RUN_MODE:
            return {"applied": False, "preview": True, "record_id": record_id}
        record = publishing_service.queue_publish_now(record_id)
        event_log_service.emit(
            aggregate_id=record_id,
            type="publish.record.queued",
            payload={"record_id": record_id},
            correlation_id=invocation.correlation_id or None,
            scopes=["publish"],
            tags=["publish", "live_apply"],
        )
        return {"applied": True, "record": record}
    raise ValueError(f"Unknown tool: {definition.name}")


mcp_gateway_service = MCPGatewayService(
    tool_executor=_tool_executor,
    resource_provider=_resource_provider,
    approval_checker=_approval_checker,
)


def _resource_scopes(resource_name: str) -> list[str] | None:
    for resource in mcp_gateway_service.resources:
        if resource.name == resource_name:
            return [resource.scope]
    return None


def _tool_scopes(tool_name: str, scopes: list[str]) -> list[str]:
    if scopes:
        return scopes
    for tool in mcp_gateway_service.tools:
        if tool.name == tool_name:
            return [tool.scope]
    return []


def _record_gateway_audit(result: dict[str, Any], *, aggregate_id: str, action: str, correlation_id: str, scopes: list[str]) -> None:
    error = result.get("error") if isinstance(result, dict) else None
    if isinstance(error, dict):
        outcome = "failed"
    else:
        outcome = "succeeded"
    event_log_service.emit_audit(
        aggregate_id=aggregate_id,
        action=action,
        outcome=outcome,
        payload={"result": result},
        correlation_id=correlation_id,
        scopes=scopes,
        tags=["mcp", "audit"],
    )


def _response_from_cache(request: Request, cached: tuple[int, dict[str, Any], dict[str, Any]]) -> Any:
    status_code, data, meta = cached
    meta = dict(meta)
    meta["idempotency_replayed"] = True
    return api_success(request, data, status_code=status_code, meta=meta)


def _store_response(client_id: str, operation: str, idempotency_key: str | None, response: tuple[int, dict[str, Any], dict[str, Any]]) -> None:
    if not idempotency_key:
        return
    idempotency_store.put(client_id, operation, idempotency_key, response)


@router.get("/runtime")
async def api_runtime_summary(request: Request):
    data = {
        "settings_summary": runtime_settings_service.summary(),
        "runtime_status": get_runtime_status(),
    }
    return api_success(request, data)


@router.patch("/runtime/live-apply")
async def api_runtime_live_apply(
    request: Request,
    payload: RuntimeLiveApplyRequest,
    x_client_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    client_id = _client_id(x_client_id)
    cached = idempotency_store.get(client_id, "runtime.live-apply", idempotency_key or "")
    if cached is not None:
        return _response_from_cache(request, cached)
    updates = payload.model_dump(exclude_none=True)
    run_id = uuid4().hex
    result = mcp_gateway_service.invoke_tool(
        "runtime.settings.update",
        {"updates": updates},
        client_id=client_id,
        run_id=run_id,
        mode=LIVE_APPLY_MODE,
        scopes=["runtime"],
        correlation_id=request.state.correlation_id,
    )
    body = {
        "run_id": run_id,
        "tool_result": result.to_dict(),
        "agent_run": mcp_gateway_service.get_run_state(run_id).to_dict(),
    }
    if not result.ok:
        return api_error_response(
            request,
            status_code=400,
            code=result.error.code,
            message=result.error.message,
            details=result.error.details,
        )
    response = (200, body, {"idempotency_replayed": False})
    _store_response(client_id, "runtime.live-apply", idempotency_key, response)
    return api_success(request, body)


@router.post("/runtime/profiles/{profile}/apply")
async def api_runtime_profile_apply(
    profile: str,
    request: Request,
    x_client_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    client_id = _client_id(x_client_id)
    operation = f"runtime.profile.apply:{profile}"
    cached = idempotency_store.get(client_id, operation, idempotency_key or "")
    if cached is not None:
        return _response_from_cache(request, cached)
    run_id = uuid4().hex
    result = mcp_gateway_service.invoke_tool(
        "runtime.profile.apply",
        {"profile": profile},
        client_id=client_id,
        run_id=run_id,
        mode=LIVE_APPLY_MODE,
        scopes=["runtime"],
        correlation_id=request.state.correlation_id,
    )
    body = {
        "run_id": run_id,
        "tool_result": result.to_dict(),
        "agent_run": mcp_gateway_service.get_run_state(run_id).to_dict(),
    }
    if not result.ok:
        return api_error_response(
            request,
            status_code=400,
            code=result.error.code,
            message=result.error.message,
            details=result.error.details,
        )
    response = (200, body, {"idempotency_replayed": False})
    _store_response(client_id, operation, idempotency_key, response)
    return api_success(request, body)


@router.get("/mcp/capabilities")
async def api_mcp_capabilities(
    request: Request,
    schema_version: str | None = Query(default=None),
    scopes: list[str] = Query(default=[]),
    features: list[str] = Query(default=[]),
):
    negotiation = mcp_gateway_service.negotiate_capabilities(
        client_schema_version=schema_version,
        client_features=features,
        client_scopes=scopes,
    )
    return api_success(request, negotiation.to_dict())


@router.get("/mcp/tools")
async def api_mcp_tools(request: Request, scopes: list[str] = Query(default=[])):
    return api_success(request, {"tools": mcp_gateway_service.list_tools(scopes or None)})


@router.get("/mcp/resources")
async def api_mcp_resources(request: Request, scopes: list[str] = Query(default=[])):
    return api_success(request, {"resources": mcp_gateway_service.list_resources(scopes or None)})


@router.get("/mcp/resources/{resource_name}")
async def api_mcp_resource_read(
    resource_name: str,
    request: Request,
    x_client_id: str | None = Header(default=None),
    limit: int | None = Query(default=None, ge=1),
    record_id: str | None = Query(default=None),
    task: str | None = Query(default=None),
):
    client_id = _client_id(x_client_id)
    if not rate_limiter.allow(client_id):
        return api_error_response(
            request,
            status_code=429,
            code="rate_limited",
            message="This client exceeded the current MCP quota window.",
            details={"client_id": client_id},
        )
    arguments = {"limit": limit, "record_id": record_id, "task": task}
    resource = mcp_gateway_service.read_resource(
        resource_name,
        arguments,
        client_id=client_id,
        scopes=_resource_scopes(resource_name),
        correlation_id=request.state.correlation_id,
    )
    _record_gateway_audit(
        resource,
        aggregate_id=resource_name,
        action=f"read:{resource_name}",
        correlation_id=request.state.correlation_id,
        scopes=_resource_scopes(resource_name) or ["read"],
    )
    if "error" in resource:
        error = resource["error"]
        return api_error_response(
            request,
            status_code=404 if error["code"] == "unknown_resource" else 403,
            code=error["code"],
            message=error["message"],
            details=error.get("details"),
        )
    return api_success(request, resource)


@router.post("/mcp/tools/{tool_name}/invoke")
async def api_mcp_invoke_tool(
    tool_name: str,
    request: Request,
    payload: MCPToolInvocationRequest,
    x_client_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    client_id = _client_id(x_client_id)
    if not rate_limiter.allow(client_id):
        return api_error_response(
            request,
            status_code=429,
            code="rate_limited",
            message="This client exceeded the current MCP quota window.",
            details={"client_id": client_id},
        )
    operation = f"mcp.invoke:{tool_name}:{payload.mode}"
    cached = idempotency_store.get(client_id, operation, idempotency_key or "")
    if cached is not None:
        return _response_from_cache(request, cached)
    run_id = payload.run_id or uuid4().hex
    result = mcp_gateway_service.invoke_tool(
        tool_name,
        payload.input,
        client_id=client_id,
        run_id=run_id,
        mode=payload.mode,
        approved=payload.approved,
        approval_token=payload.approval_token,
        scopes=_tool_scopes(tool_name, payload.scopes),
        correlation_id=request.state.correlation_id,
    )
    result_payload = result.to_dict()
    _record_gateway_audit(
        result_payload,
        aggregate_id=run_id,
        action=f"tool:{tool_name}",
        correlation_id=request.state.correlation_id,
        scopes=_tool_scopes(tool_name, payload.scopes) or ["runtime"],
    )
    if not result.ok:
        status_code = 403 if result.error.code in {"approval_required", "scope_denied"} else 400
        return api_error_response(
            request,
            status_code=status_code,
            code=result.error.code,
            message=result.error.message,
            details=result.error.details,
        )
    body = {
        "run_id": run_id,
        "tool_result": result_payload,
        "agent_run": mcp_gateway_service.get_run_state(run_id).to_dict(),
    }
    response = (200, body, {"idempotency_replayed": False})
    _store_response(client_id, operation, idempotency_key, response)
    return api_success(request, body)


@router.get("/agent-runs/{run_id}")
async def api_agent_run(run_id: str, request: Request):
    state = mcp_gateway_service.get_run_state(run_id)
    if state is None:
        return api_error_response(
            request,
            status_code=404,
            code="run_not_found",
            message=f"Agent run {run_id} was not found.",
        )
    return api_success(request, state.to_dict())


@router.get("/events")
async def api_events(
    request: Request,
    aggregate_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    since_event_id: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
):
    try:
        events = event_log_service.replay(
            aggregate_id=aggregate_id,
            event_type=event_type,
            since_event_id=since_event_id,
            limit=limit,
        )
    except KeyError:
        return api_error_response(
            request,
            status_code=404,
            code="event_cursor_not_found",
            message=f"Event cursor {since_event_id} was not found.",
        )
    return api_success(request, {"events": [event.to_dict() for event in events]})


@router.get("/events/stream")
async def api_events_stream(
    request: Request,
    aggregate_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    since_event_id: str | None = Query(default=None),
    replay_only: bool = Query(default=False),
):
    subscription = event_log_service.subscribe()

    async def _stream():
        try:
            try:
                backlog = event_log_service.replay(
                    aggregate_id=aggregate_id,
                    event_type=event_type,
                    since_event_id=since_event_id,
                )
            except KeyError:
                payload = {
                    "error": {
                        "code": "event_cursor_not_found",
                        "message": f"Event cursor {since_event_id} was not found.",
                    }
                }
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                return
            for event in backlog:
                yield f"id: {event.event_id}\nevent: {event.type}\ndata: {json.dumps(event.to_dict())}\n\n"
            if replay_only:
                return
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(subscription.queue.get, True, 1.0)
                except Empty:
                    yield ": keepalive\n\n"
                    continue
                if aggregate_id is not None and event.aggregate_id != aggregate_id:
                    continue
                if event_type is not None and event.type != event_type:
                    continue
                yield f"id: {event.event_id}\nevent: {event.type}\ndata: {json.dumps(event.to_dict())}\n\n"
        finally:
            subscription.close()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
