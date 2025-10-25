"""Error handling utilities providing uniform JSON responses."""

from __future__ import annotations

from typing import Optional, cast

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from chart_mcp.types import JSONDict, JSONValue
from chart_mcp.utils.logging import get_trace_id


class ApiError(Exception):
    """Base application exception carrying a machine-friendly code."""

    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        details: Optional[JSONValue] = None,
        code: str | None = None,
    ) -> None:
        """Capture the human message, optional structured details and override code."""
        super().__init__(message)
        self.message = message
        # ``details`` defaults to an empty dict so callers can attach structured
        # metadata without falling back to ``Any``.
        self.details: JSONValue = details if details is not None else {}
        # Individual error instances may supply a more specific machine-friendly
        # code (e.g. ``forbidden:chat``) without the need for bespoke subclasses.
        self.code = code or self.__class__.code

    def to_payload(self) -> JSONDict:
        """Return the standard error document used across HTTP handlers."""
        return {
            "error": {"code": self.code, "message": self.message},
            "details": self.details,
            "trace_id": get_trace_id(),
        }


class BadRequest(ApiError):
    """Exception raised when user input is invalid."""

    status_code = 400
    code = "bad_request"


class Unauthorized(ApiError):
    """Exception raised when the API token validation fails."""

    status_code = 401
    code = "unauthorized"


class Forbidden(ApiError):
    """Exception raised when the caller is authenticated but not authorized."""

    status_code = 403
    code = "forbidden"


class UpstreamError(ApiError):
    """Exception raised when an external dependency (exchange) fails."""

    status_code = 502
    code = "upstream_error"


class TooManyRequests(ApiError):
    """Exception raised when a caller exceeds the configured rate limit."""

    status_code = 429
    code = "too_many_requests"


class NotFound(ApiError):
    """Exception raised when a resource cannot be located."""

    status_code = 404
    code = "not_found"


def api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a standardized JSON response for custom exceptions."""
    assert isinstance(exc, ApiError)
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Translate FastAPI HTTPException into project JSON schema."""
    assert isinstance(exc, HTTPException)
    payload: JSONDict = {
        "error": {"code": "http_error", "message": exc.detail},
        "details": {},
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    payload: JSONDict = {
        "error": {"code": "internal_error", "message": str(exc)},
        "details": {},
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=500, content=payload)


def request_validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a consistent payload for FastAPI validation errors."""
    assert isinstance(exc, RequestValidationError)
    raw_errors = exc.errors()

    def _serialize(value: object) -> object:
        """Convert non-serializable values such as exceptions to strings."""
        if isinstance(value, Exception):
            return str(value)
        if isinstance(value, dict):
            return {str(k): _serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_serialize(item) for item in value]
        return value

    formatted_errors = [
        {str(key): _serialize(value) for key, value in error.items()} for error in raw_errors
    ]
    details: list[object] = [cast(object, error) for error in formatted_errors]
    payload: JSONDict = {
        "error": {"code": "validation_error", "message": "Request validation failed"},
        "details": details,
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=422, content=payload)


__all__ = [
    "ApiError",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "UpstreamError",
    "TooManyRequests",
    "NotFound",
    "api_error_handler",
    "http_exception_handler",
    "unexpected_exception_handler",
    "request_validation_exception_handler",
]
