"""Error handling utilities providing uniform JSON responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from chart_mcp.utils.logging import get_trace_id


class ApiError(Exception):
    """Base application exception carrying a machine-friendly code."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BadRequest(ApiError):
    """Exception raised when user input is invalid."""

    status_code = 400
    code = "bad_request"


class Unauthorized(ApiError):
    """Exception raised when the API token validation fails."""

    status_code = 401
    code = "unauthorized"


class UpstreamError(ApiError):
    """Exception raised when an external dependency (exchange) fails."""

    status_code = 502
    code = "upstream_error"


def api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a standardized JSON response for custom exceptions."""
    assert isinstance(exc, ApiError)
    payload = {
        "code": exc.code,
        "message": exc.message,
        "details": exc.details,
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Translate FastAPI HTTPException into project JSON schema."""
    assert isinstance(exc, HTTPException)
    payload = {
        "code": "http_error",
        "message": exc.detail,
        "details": {},
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    payload = {
        "code": "internal_error",
        "message": str(exc),
        "details": {},
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=500, content=payload)
