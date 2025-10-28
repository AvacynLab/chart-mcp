"""Structured logging utilities leveraging loguru.

The project exposes a fairly involved streaming pipeline; downstream
observability (dashboards, alerts, incident response) relies on
structured logs exposing both transport metadata (request identifier) and
domain specific context (stage, symbol, timeframe, latency).  This module
provides helpers to configure loguru accordingly and convenience APIs for
routes/services to enrich the context in a disciplined manner.
"""

from __future__ import annotations

import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterator

from fastapi import Request, Response
from loguru import logger

from chart_mcp.config import get_settings


@dataclass
class RequestLogContext:
    """State carried across the lifecycle of a request for logging.

    Attributes
    ----------
    symbol:
        Trading pair currently being processed (e.g. ``BTC/USDT``).  Populated
        by REST and SSE routes once the request payload is validated.
    timeframe:
        Candlestick timeframe associated with the request (``1m``, ``1h``, ...).
    stage:
        Name of the logical pipeline stage currently executing.  Defaults to
        ``None`` until the :func:`log_stage` context manager is invoked.
    stage_started_at:
        Timestamp (``time.perf_counter``) recorded when the active stage began.
        Used to compute latency for ``stage.completed`` / ``stage.failed`` logs.

    """

    symbol: str | None = None
    timeframe: str | None = None
    stage: str | None = None
    stage_started_at: float | None = None


_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="unknown")
_REQUEST_CONTEXT: ContextVar[RequestLogContext | None] = ContextVar("request_context", default=None)


def configure_logging() -> None:
    """Configure loguru to output JSON logs with a trace identifier."""
    settings = get_settings()
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level.upper(), serialize=True)


def get_trace_id() -> str:
    """Return the current request trace identifier."""
    return _TRACE_ID.get()


def get_request_context() -> RequestLogContext:
    """Return the current structured logging context."""
    context = _REQUEST_CONTEXT.get()
    if context is None:
        context = RequestLogContext()
        _REQUEST_CONTEXT.set(context)
    return context


def set_request_metadata(*, symbol: str | None = None, timeframe: str | None = None) -> None:
    """Enrich the structured context with symbol and timeframe information."""
    context = get_request_context()
    if symbol is not None:
        context.symbol = symbol
    if timeframe is not None:
        context.timeframe = timeframe


@contextmanager
def log_stage(stage: str) -> Iterator[None]:
    """Context manager logging stage completion/failure with latency metrics."""
    context = get_request_context()
    previous_stage = context.stage
    previous_started_at = context.stage_started_at
    context.stage = stage
    context.stage_started_at = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed_ms = 0.0
        if context.stage_started_at is not None:
            elapsed_ms = (time.perf_counter() - context.stage_started_at) * 1000
        logger.bind(
            request_id=get_trace_id(),
            trace_id=get_trace_id(),
            stage=stage,
            latency_ms=elapsed_ms,
            symbol=context.symbol,
            timeframe=context.timeframe,
        ).exception("stage.failed")
        raise
    else:
        elapsed_ms = 0.0
        if context.stage_started_at is not None:
            elapsed_ms = (time.perf_counter() - context.stage_started_at) * 1000
        logger.bind(
            request_id=get_trace_id(),
            trace_id=get_trace_id(),
            stage=stage,
            latency_ms=elapsed_ms,
            symbol=context.symbol,
            timeframe=context.timeframe,
        ).info("stage.completed")
    finally:
        context.stage = previous_stage
        context.stage_started_at = previous_started_at


async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """FastAPI middleware injecting a trace identifier into logging context."""
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    trace_token = _TRACE_ID.set(trace_id)
    context_token = _REQUEST_CONTEXT.set(RequestLogContext())
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code if response is not None else 500
        context = get_request_context()
        # The middleware purposely only logs method, path, status and duration to
        # avoid leaking sensitive headers such as ``Authorization`` while still
        # providing enough context for observability dashboards.
        logger.bind(
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            latency_ms=duration_ms,
            trace_id=trace_id,
            request_id=trace_id,
            stage=context.stage or "request",
            symbol=context.symbol,
            timeframe=context.timeframe,
        ).info("request.completed")
        _TRACE_ID.reset(trace_token)
        _REQUEST_CONTEXT.reset(context_token)
    if response is None:
        raise RuntimeError("Downstream middleware returned no response object")
    response.headers["X-Trace-Id"] = trace_id
    return response
