"""Structured logging utilities leveraging loguru."""

from __future__ import annotations

import sys
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger

from chart_mcp.config import get_settings

_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="unknown")


def configure_logging() -> None:
    """Configure loguru to output JSON logs with a trace identifier."""
    settings = get_settings()
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level.upper(), serialize=True)


def get_trace_id() -> str:
    """Return the current request trace identifier."""
    return _TRACE_ID.get()


async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """FastAPI middleware injecting a trace identifier into logging context."""
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    token = _TRACE_ID.set(trace_id)
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code if response is not None else 500
        # The middleware purposely only logs method, path, status and duration to
        # avoid leaking sensitive headers such as ``Authorization`` while still
        # providing enough context for observability dashboards.
        logger.bind(
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            trace_id=trace_id,
        ).info("request.completed")
        _TRACE_ID.reset(token)
    if response is None:
        raise RuntimeError("Downstream middleware returned no response object")
    response.headers["X-Trace-Id"] = trace_id
    return response
