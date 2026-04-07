"""MCP gateway routes exposed under the versioned public API."""
from __future__ import annotations

import copy
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..api.contracts import (
    MCPCapabilityResponse,
    MCPResourceListResponse,
    MCPResourceReadResponse,
    MCPToolInvocationRequest,
    MCPToolInvocationResponse,
    MCPToolListResponse,
)
from ..api.errors import (
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_REPLAY_HEADER,
    ApiError,
    error_responses,
)
from ..api.idempotency import fingerprint_payload, idempotency_store
from ..dependencies import (
    get_eventing_service,
    get_metadata_service,
    get_progress_service,
    get_publishing_service,
    get_record_query_service,
    runtime_settings_service,
)
from ..prompts import read_prompt_runs
from ..runtime import get_runtime_status
from ..services.mcp_gateway import DRY_RUN_MODE, LIVE_APPLY_MODE, MCPGatewayService, ToolDefinition, ToolInvocation
from ..services.runtime_settings import RuntimeSettingsService

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP Gateway"])


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


rate_limiter = _SimpleRateLimiter(max_requests=60, window_seconds=60)


def _client_id(explicit: str | None) -> str:
    return (explicit or "").strip() or "anonymous"


def _idempotency_scope(path: str, key: str) -> str:
    return f"mcp:{path}:{key}"


def _idempotency_replay(path: str, key: str | None, fingerprint: str) -> JSONResponse | None:
    if not key:
        return None
    try:
        stored = idempotency_store.lookup(_idempotency_scope(path, key), fingerprint)
    except ValueError as exc:
        raise ApiError(status_code=409, code="idempotency_key_reused", message=str(exc)) from exc
    if stored is None:
        return None
    return JSONResponse(
        status_code=stored.status_code,
        content=stored.body,
        headers={IDEMPOTENCY_REPLAY_HEADER: "true"},
    )


def _store_idempotent_response(path: str, key: str | None, fingerprint: str | None, body: dict[str, Any], status_code: int) -> None:
    if not key or not fingerprint:
        return
    idempotency_store.store_response(
        _idempotency_scope(path, key),
        fingerprint=fingerprint,
        status_code=status_code,
        body=jsonable_encoder(body),
    )


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
    records = get_record_query_service().list_recent_records(get_metadata_service(), get_progress_service())
    visible = records[:limit] if limit is not None else records
    return {"count": len(records), "records": visible}


def _prompt_run_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    record_id = str(arguments.get("record_id", "") or "").strip() or None
    task = str(arguments.get("task", "") or "").strip() or None
    limit = int(arguments.get("limit", 10) or 10)
    runs = read_prompt_runs(record_id=record_id, task=task)
    runs.sort(key=lambda item: item.get("completed_at", ""), reverse=True)
    return {"count": len(runs), "runs": runs[:limit]}


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
        "provider_status": get_publishing_service().get_provider_status("youtube", redirect_uri=None),
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
    return {"resource": definition.name}


def _approval_checker(invocation: ToolInvocation, definition: ToolDefinition) -> bool:
    return invocation.approval_token == "approved"


def _emit_gateway_event(event_type: str, *, aggregate_id: str, payload: dict[str, Any], correlation_id: str, run_id: str | None = None) -> None:
    get_eventing_service().emit(
        event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        correlation_id=correlation_id,
        run_id=run_id,
        source="mcp_gateway",
    )


def _tool_executor(invocation: ToolInvocation, definition: ToolDefinition) -> dict[str, Any]:
    if definition.name == "runtime.settings.read":
        return {
            "settings_summary": runtime_settings_service.summary(),
            "runtime_status": get_runtime_status(),
        }
    if definition.name == "runtime.settings.update":
        updates = dict(invocation.arguments.get("updates") or {})
        if invocation.mode == DRY_RUN_MODE:
            return {"applied": False, "preview": True, "resolved_settings": _preview_runtime_settings(updates)}
        resolved = runtime_settings_service.update_user_settings(updates)
        _emit_gateway_event(
            "mcp.runtime.settings.updated",
            aggregate_id="runtime-settings",
            payload={"updates": updates, "resolved_settings": resolved},
            correlation_id=invocation.correlation_id,
            run_id=invocation.run_id,
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
            return {"applied": False, "preview": True, "profile": profile, "resolved_settings": _preview_runtime_profile(profile)}
        resolved = runtime_settings_service.apply_runtime_profile(profile)
        _emit_gateway_event(
            "mcp.runtime.profile.applied",
            aggregate_id="runtime-settings",
            payload={"profile": profile, "resolved_settings": resolved},
            correlation_id=invocation.correlation_id,
            run_id=invocation.run_id,
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
            return {"applied": False, "preview": True, "keys": sorted(updates)}
        statuses = runtime_settings_service.update_secrets(updates)
        _emit_gateway_event(
            "mcp.credentials.updated",
            aggregate_id="runtime-secrets",
            payload={"keys": sorted(updates)},
            correlation_id=invocation.correlation_id,
            run_id=invocation.run_id,
        )
        return {"applied": True, "secret_status": statuses}
    if definition.name == "publish.record":
        record_id = str(invocation.arguments.get("record_id", "")).strip()
        if invocation.mode == DRY_RUN_MODE:
            return {"applied": False, "preview": True, "record_id": record_id}
        record = get_publishing_service().queue_publish_now(record_id)
        _emit_gateway_event(
            "mcp.publish.record.queued",
            aggregate_id=record_id,
            payload={"record_id": record_id},
            correlation_id=invocation.correlation_id,
            run_id=invocation.run_id,
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


@router.get("/capabilities", response_model=MCPCapabilityResponse, responses=error_responses())
async def mcp_capabilities(
    schema_version: str | None = Query(default=None),
    scopes: list[str] = Query(default=[]),
    features: list[str] = Query(default=[]),
) -> dict[str, Any]:
    negotiation = mcp_gateway_service.negotiate_capabilities(
        client_schema_version=schema_version,
        client_features=features,
        client_scopes=scopes,
    )
    return negotiation.to_dict()


@router.get("/tools", response_model=MCPToolListResponse, responses=error_responses())
async def mcp_tools(scopes: list[str] = Query(default=[])) -> dict[str, Any]:
    return {"tools": mcp_gateway_service.list_tools(scopes or None)}


@router.get("/resources", response_model=MCPResourceListResponse, responses=error_responses())
async def mcp_resources(scopes: list[str] = Query(default=[])) -> dict[str, Any]:
    return {"resources": mcp_gateway_service.list_resources(scopes or None)}


@router.get("/resources/{resource_name}", response_model=MCPResourceReadResponse, responses=error_responses())
async def mcp_resource_read(
    resource_name: str,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    limit: int | None = Query(default=None, ge=1),
    record_id: str | None = Query(default=None),
    task: str | None = Query(default=None),
) -> dict[str, Any]:
    client_id = _client_id(x_client_id)
    if not rate_limiter.allow(client_id):
        raise ApiError(status_code=429, code="rate_limited", message="This client exceeded the current MCP quota window.")
    arguments = {"limit": limit, "record_id": record_id, "task": task}
    payload = mcp_gateway_service.read_resource(
        resource_name,
        arguments,
        client_id=client_id,
        scopes=_resource_scopes(resource_name),
    )
    if "error" in payload:
        error = payload["error"]
        status_code = 404 if error["code"] == "unknown_resource" else 403
        raise ApiError(status_code=status_code, code=error["code"], message=error["message"], details=error.get("details"))
    _emit_gateway_event(
        "mcp.resource.read",
        aggregate_id=resource_name,
        payload={"resource": resource_name, "client_id": client_id},
        correlation_id="resource-read",
    )
    return {"resource": resource_name, "payload": payload}


@router.post("/tools/{tool_name}/invoke", response_model=MCPToolInvocationResponse, responses=error_responses())
async def mcp_invoke_tool(
    tool_name: str,
    payload: MCPToolInvocationRequest,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict[str, Any] | JSONResponse:
    client_id = _client_id(x_client_id)
    if not rate_limiter.allow(client_id):
        raise ApiError(status_code=429, code="rate_limited", message="This client exceeded the current MCP quota window.")
    request_payload = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    fingerprint = fingerprint_payload({"tool_name": tool_name, **request_payload})
    replay = _idempotency_replay(f"/api/v1/mcp/tools/{tool_name}/invoke", idempotency_key, fingerprint)
    if replay is not None:
        return replay
    run_id = str(uuid4())
    result = mcp_gateway_service.invoke_tool(
        tool_name,
        payload.input,
        client_id=client_id,
        run_id=run_id,
        mode=payload.mode,
        approved=payload.approved,
        approval_token=payload.approval_token or "",
        scopes=_tool_scopes(tool_name, payload.scopes),
        correlation_id=x_correlation_id or run_id,
    )
    if not result.ok:
        status_code = 403 if result.error.code in {"approval_required", "scope_denied"} else 400
        raise ApiError(status_code=status_code, code=result.error.code, message=result.error.message, details=result.error.details)
    body = {
        "run_id": run_id,
        "tool_result": result.to_dict(),
        "agent_run": mcp_gateway_service.get_run_state(run_id).to_dict(),
    }
    _store_idempotent_response(f"/api/v1/mcp/tools/{tool_name}/invoke", idempotency_key, fingerprint, body, 200)
    return body
