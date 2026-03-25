"""API response helpers, correlation IDs, and error handling."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_ID_HEADER = "X-Correlation-ID"
_correlation_id_var: ContextVar[str] = ContextVar("clipmato_correlation_id", default="")


def get_correlation_id() -> str:
    """Return the active request correlation ID, if any."""
    return _correlation_id_var.get("")


def request_correlation_id(request: Request) -> str:
    """Resolve the correlation ID from request state or fall back to a new ID."""
    correlation_id = getattr(request.state, "correlation_id", "") or ""
    return correlation_id or uuid4().hex


def api_error_body(correlation_id: str, code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build the standard machine-readable API error object."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def api_success(request: Request, data: Any, *, status_code: int = 200, meta: dict[str, Any] | None = None) -> JSONResponse:
    """Wrap successful API responses in a stable envelope."""
    correlation_id = request_correlation_id(request)
    payload: dict[str, Any] = {
        "data": data,
        "meta": {
            "correlation_id": correlation_id,
        },
    }
    if meta:
        payload["meta"].update(meta)
    return JSONResponse(payload, status_code=status_code, headers={CORRELATION_ID_HEADER: correlation_id})


def api_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Return a standard API error response."""
    correlation_id = request_correlation_id(request)
    return JSONResponse(
        api_error_body(correlation_id, code, message, details),
        status_code=status_code,
        headers={CORRELATION_ID_HEADER: correlation_id},
    )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to each request and response."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_ID_HEADER, "").strip() or uuid4().hex
        request.state.correlation_id = correlation_id
        token = _correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id_var.reset(token)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


async def api_http_exception_handler(request: Request, exc: HTTPException):
    """Emit stable JSON errors for versioned API routes."""
    if not request.url.path.startswith("/api/v1/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    return api_error_response(
        request,
        status_code=exc.status_code,
        code="http_error",
        message=str(exc.detail),
        details={"headers": exc.headers or {}},
    )


async def api_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Emit stable validation errors for versioned API routes."""
    if not request.url.path.startswith("/api/v1/"):
        return JSONResponse({"detail": exc.errors()}, status_code=422)
    return api_error_response(
        request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )


async def api_unhandled_exception_handler(request: Request, exc: Exception):
    """Emit stable internal errors for versioned API routes."""
    if not request.url.path.startswith("/api/v1/"):
        raise exc
    return api_error_response(
        request,
        status_code=500,
        code="internal_error",
        message="The server could not complete this request.",
        details={"exception": type(exc).__name__},
    )
