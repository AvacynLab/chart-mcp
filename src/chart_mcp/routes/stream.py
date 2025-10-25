"""Streaming route for SSE analysis."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable
from typing import Annotated, Dict, List, cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/stream",
    tags=["stream"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_streaming_service(request: Request) -> StreamingService:
    """Retrieve the streaming service from application state."""
    return cast(StreamingService, request.app.state.streaming_service)


@router.get("/analysis")
async def stream_analysis(
    symbol: Annotated[str, Query(..., min_length=3, max_length=20)],
    timeframe: Annotated[str, Query(...)],
    indicators: Annotated[
        List[str],
        Query(default_factory=list, description="Indicator names such as ema,rsi"),
    ],
    streaming_service: Annotated[StreamingService, Depends(get_streaming_service)],
    limit: Annotated[
        int,
        Query(ge=1, description="Number of OHLCV rows requested for the stream (1-5000)."),
    ] = 500,
) -> StreamingResponse:
    """Stream analysis events using Server-Sent Events."""
    parse_timeframe(timeframe)
    if limit > 5000:
        # FastAPI already enforces the ``ge`` lower bound. We keep the upper bound
        # on our side so the resulting error payload aligns with the rest of the API.
        raise BadRequest("limit must be between 1 and 5000 for streaming analysis")
    if len(indicators) > 10:
        raise BadRequest("A maximum of 10 indicators can be requested per stream")
    cleaned_indicators: List[str] = []
    for raw_indicator in indicators:
        indicator = raw_indicator.strip()
        if not indicator:
            raise BadRequest("Indicator names cannot be empty")
        cleaned_indicators.append(indicator)
    indicator_specs: List[Dict[str, object]]
    if cleaned_indicators:
        indicator_specs = [{"name": name, "params": {}} for name in cleaned_indicators]
    else:
        indicator_specs = [
            # Fall back to EMA and RSI defaults for streaming heuristics.
            {"name": "ema", "params": {"window": 50}},
            {"name": "rsi", "params": {"window": 14}},
        ]
    iterator = await streaming_service.stream_analysis(
        symbol, timeframe, indicator_specs, limit=limit
    )

    async def _cancellation_guard() -> AsyncIterator[str]:
        """Yield SSE chunks and ensure graceful shutdown on cancellation."""
        try:
            async for chunk in iterator:
                yield chunk
        except asyncio.CancelledError:
            # Explicitly close the generator so the underlying streamer stops the
            # heartbeat task and avoids dangling background work.
            closer = getattr(iterator, "aclose", None)
            if callable(closer):
                maybe_coro = closer()
                if inspect.isawaitable(maybe_coro):
                    # ``cast`` communicates to the type-checker that the awaitable
                    # conforms to the protocol even though ``isawaitable`` only
                    # returns a ``bool`` at runtime.
                    await cast(Awaitable[object], maybe_coro)
            stopper = getattr(iterator, "stop", None)
            if callable(stopper):
                stop_result = stopper()
                if inspect.isawaitable(stop_result):
                    await cast(Awaitable[object], stop_result)
            raise

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_cancellation_guard(), media_type="text/event-stream", headers=headers)
