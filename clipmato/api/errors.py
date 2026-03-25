"""Error handling and request correlation for the public API."""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .contracts import MachineErrorEnvelope

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_REPLAY_HEADER = "X-Idempotency-Replayed"
API_VERSION = "v1"
API_VERSION_HEADER = "X-Clipmato-API-Version"
_correlation_id_ctx: ContextVar[str] = ContextVar("clipmato_correlation_id", default="-")


class ApiError(Exception):
    """Structured exception for public API failures."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def is_api_request(request: Request) -> bool:
    """Return whether the current request targets the versioned public API."""
    return request.url.path.startswith("/api/v1/")


def current_correlation_id() -> str:
    """Return the correlation ID for the current request context."""
    return _correlation_id_ctx.get()


def get_correlation_id(request: Request) -> str:
    """Return the request correlation ID, generating a fallback if needed."""
    correlation_id = getattr(request.state, "correlation_id", "")
    if correlation_id:
        return str(correlation_id)
    return current_correlation_id() or "-"


def error_responses() -> dict[int | str, dict[str, Any]]:
    """OpenAPI response declarations shared by public API endpoints."""
    return {
        400: {"model": MachineErrorEnvelope, "description": "Bad request"},
        404: {"model": MachineErrorEnvelope, "description": "Resource not found"},
        409: {"model": MachineErrorEnvelope, "description": "Idempotency key conflict"},
        413: {"model": MachineErrorEnvelope, "description": "Payload too large"},
        415: {"model": MachineErrorEnvelope, "description": "Unsupported media type"},
        422: {"model": MachineErrorEnvelope, "description": "Validation error"},
        500: {"model": MachineErrorEnvelope, "description": "Internal server error"},
    }


def _default_code_for_status(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 413:
        return "payload_too_large"
    if status_code == 415:
        return "unsupported_media_type"
    if status_code == 422:
        return "validation_error"
    if status_code >= 500:
        return "internal_server_error"
    return "request_failed"


def _map_http_exception_code(status_code: int, detail: Any) -> str:
    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
        return detail["code"]

    message = str(detail or "").lower()
    if status_code == 404 and "record not found" in message:
        return "record_not_found"
    if status_code == 404 and "preset" in message:
        return "project_preset_not_found"
    if status_code == 409 and "idempotency" in message:
        return "idempotency_key_reused"
    if status_code == 413 or "file too large" in message:
        return "payload_too_large"
    if status_code == 415 or "unsupported media type" in message:
        return "unsupported_media_type"
    return _default_code_for_status(status_code)


def build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a standard public API error response."""
    correlation_id = get_correlation_id(request)
    payload = MachineErrorEnvelope(
        correlation_id=correlation_id,
        error={
            "code": code,
            "status": status_code,
            "message": message,
            "details": details,
        },
    )
    encoded = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return JSONResponse(
        status_code=status_code,
        content=encoded,
        headers={
            CORRELATION_ID_HEADER: correlation_id,
            API_VERSION_HEADER: API_VERSION,
        },
    )


def api_error_from_http_exception(exc: HTTPException) -> ApiError:
    """Convert an HTTPException into a structured ApiError."""
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        details = detail.get("details") if isinstance(detail.get("details"), dict) else None
    else:
        message = str(detail or "Request failed")
        details = None
    return ApiError(
        status_code=exc.status_code,
        code=_map_http_exception_code(exc.status_code, detail),
        message=message,
        details=details,
    )


async def correlation_id_middleware(request: Request, call_next):
    """Attach correlation IDs to request state, logs, and response headers."""
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
    request.state.correlation_id = correlation_id
    token = _correlation_id_ctx.set(correlation_id)
    logger.info(
        "HTTP request started method=%s path=%s correlation_id=%s",
        request.method,
        request.url.path,
        correlation_id,
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "HTTP request failed method=%s path=%s correlation_id=%s",
            request.method,
            request.url.path,
            correlation_id,
        )
        raise
    else:
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        if is_api_request(request):
            response.headers[API_VERSION_HEADER] = API_VERSION
        logger.info(
            "HTTP request completed method=%s path=%s status=%s correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            correlation_id,
        )
        return response
    finally:
        _correlation_id_ctx.reset(token)


def register_api_exception_handlers(app: FastAPI) -> None:
    """Install structured exception handlers for the versioned public API."""

    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return build_error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(HTTPException)
    async def _http_error_handler(request: Request, exc: HTTPException):
        if not is_api_request(request):
            return await http_exception_handler(request, exc)
        api_error = api_error_from_http_exception(exc)
        return await _api_error_handler(request, api_error)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError):
        if not is_api_request(request):
            return await request_validation_exception_handler(request, exc)
        return build_error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details={"issues": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled application error on %s", request.url.path)
        if not is_api_request(request):
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
        return build_error_response(
            request,
            status_code=500,
            code="internal_server_error",
            message="Internal server error.",
        )
