"""Tests covering the structured logging middleware."""

from __future__ import annotations

import json

import pytest
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response

from chart_mcp.utils.logging import logging_middleware


@pytest.mark.anyio
async def test_logging_middleware_emits_sanitised_record() -> None:
    """The middleware should log bounded context without leaking secrets."""
    captured: list[str] = []
    logger.remove()
    sink_id = logger.add(captured.append, serialize=True)
    try:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/finance",
            "raw_path": b"/finance",
            "headers": [
                (b"authorization", b"Bearer super-secret"),
                (b"x-trace-id", b"trace-123"),
            ],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
            "app": None,
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request(scope, receive)

        async def call_next(_: Request) -> Response:
            return Response("ok", status_code=204)

        response = await logging_middleware(request, call_next)
    finally:
        logger.remove(sink_id)

    assert response.headers["X-Trace-Id"] == "trace-123"
    assert captured, "Expected logging middleware to emit a record"
    payload = json.loads(captured[-1])
    record = payload["record"]
    assert record["message"] == "request.completed"
    extra = record["extra"]
    assert extra["status_code"] == 204
    assert extra["method"] == "GET"
    assert extra["path"] == "/finance"
    assert "super-secret" not in json.dumps(payload).lower()
