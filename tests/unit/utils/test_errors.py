"""Tests covering the JSON helpers exposed by :mod:`chart_mcp.utils.errors`."""

from __future__ import annotations

import json

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from chart_mcp.utils.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unexpected_exception_handler,
)


def _make_request() -> Request:
    """Return a minimal ASGI request used when invoking the handlers directly."""
    scope = {"type": "http", "method": "GET", "path": "/tests"}
    return Request(scope)


def _parse_json(response) -> dict[str, object]:
    """Decode the JSON response body emitted by the handler under test."""
    body = response.body
    assert body is not None
    return json.loads(body.decode("utf-8"))


def test_api_error_handler_serialises_payload() -> None:
    """Custom :class:`ApiError` instances should map to deterministic payloads."""
    request = _make_request()
    error = ApiError("boom", details={"context": "unit"}, code="custom_error")
    response = api_error_handler(request, error)

    assert response.status_code == error.status_code
    payload = _parse_json(response)
    assert payload["error"] == {"code": "custom_error", "message": "boom"}
    assert payload["details"] == {"context": "unit"}
    assert "trace_id" in payload


def test_http_exception_handler_wraps_fastapi_exceptions() -> None:
    """Ensure :class:`HTTPException` objects are converted to our schema."""
    request = _make_request()
    exc = HTTPException(status_code=418, detail="teapot")
    response = http_exception_handler(request, exc)

    assert response.status_code == 418
    payload = _parse_json(response)
    assert payload["error"] == {"code": "http_error", "message": "teapot"}
    assert payload["details"] == {}
    assert "trace_id" in payload


def test_request_validation_exception_handler_serialises_errors() -> None:
    """Validation errors should be serialised into the details list."""
    request = _make_request()
    exc = RequestValidationError(
        [
            {
                "loc": ("query", "limit"),
                "msg": "value is not a valid integer",
                "type": "type_error.integer",
            }
        ]
    )
    response = request_validation_exception_handler(request, exc)

    assert response.status_code == 422
    payload = _parse_json(response)
    assert payload["error"]["code"] == "validation_error"
    assert payload["details"] == [
        {
            "loc": ["query", "limit"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        }
    ]


def test_unexpected_exception_handler_masks_internal_details() -> None:
    """Unexpected exceptions should emit a generic error payload."""
    request = _make_request()
    response = unexpected_exception_handler(request, RuntimeError("secret"))

    assert response.status_code == 500
    payload = _parse_json(response)
    assert payload["error"] == {"code": "internal_error", "message": "secret"}
    assert payload["details"] == {}
    assert "trace_id" in payload

