"""Unit tests covering structured logging helpers."""

from __future__ import annotations

import json
from typing import List

import anyio
import pytest
from fastapi import Response
from loguru import logger
from starlette.requests import Request

from chart_mcp.utils.logging import (
    configure_logging,
    log_stage,
    logging_middleware,
    set_request_metadata,
)


def _build_request(path: str, trace_id: str = "trace-123") -> Request:
    """Construct a Starlette request compatible with the middleware tests."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "root_path": "",
        "scheme": "http",
        "headers": [
            (b"x-trace-id", trace_id.encode("utf-8")),
            (b"host", b"testserver"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "query_string": b"",
        "app": object(),
    }

    async def _receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, _receive)


@pytest.mark.anyio
async def test_logging_middleware_includes_request_metadata() -> None:
    """The middleware should record request identifiers and domain metadata."""
    configure_logging()
    events: List[str] = []
    handler_id = logger.add(events.append, serialize=True)
    request = _build_request("/health", trace_id="req-001")

    async def _call_next(_: Request) -> Response:
        set_request_metadata(symbol="BTC/USDT", timeframe="1h")
        return Response(status_code=204)

    try:
        response = await logging_middleware(request, _call_next)
        assert response.headers["X-Trace-Id"] == "req-001"
    finally:
        logger.remove(handler_id)

    records = [json.loads(event)["record"] for event in events]
    request_records = [rec for rec in records if rec["message"] == "request.completed"]
    assert request_records, "request log entry should be emitted"
    extra = request_records[0]["extra"]
    assert extra["request_id"] == "req-001"
    assert extra["trace_id"] == "req-001"
    assert extra["symbol"] == "BTC/USDT"
    assert extra["timeframe"] == "1h"
    assert extra["stage"] == "request"
    assert extra["latency_ms"] >= 0.0


@pytest.mark.anyio
async def test_log_stage_records_latency_and_metadata() -> None:
    """log_stage should emit completion logs enriched with context metadata."""
    configure_logging()
    events: List[str] = []
    handler_id = logger.add(events.append, serialize=True)
    request = _build_request("/analysis", trace_id="req-002")

    async def _call_next(_: Request) -> Response:
        set_request_metadata(symbol="ETH/USDT", timeframe="5m")
        with log_stage("indicators"):
            await anyio.sleep(0.01)
        return Response(status_code=200)

    try:
        await logging_middleware(request, _call_next)
    finally:
        logger.remove(handler_id)

    records = [json.loads(event)["record"] for event in events]
    stage_logs = [rec for rec in records if rec["message"] == "stage.completed"]
    assert stage_logs, "stage.completed log should be emitted"
    extra = stage_logs[0]["extra"]
    assert extra["stage"] == "indicators"
    assert extra["symbol"] == "ETH/USDT"
    assert extra["timeframe"] == "5m"
    assert extra["request_id"] == "req-002"
    assert extra["latency_ms"] >= 0.0
