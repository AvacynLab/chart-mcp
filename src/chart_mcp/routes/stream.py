"""Streaming route for SSE analysis."""

from __future__ import annotations

from typing import Annotated, Dict, List, cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from chart_mcp.routes.auth import require_token
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/stream", tags=["stream"], dependencies=[Depends(require_token)])


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
) -> StreamingResponse:
    """Stream analysis events using Server-Sent Events."""
    parse_timeframe(timeframe)
    indicator_specs: List[Dict[str, object]]
    if indicators:
        indicator_specs = [{"name": name, "params": {}} for name in indicators]
    else:
        indicator_specs = [
            # Fall back to EMA and RSI defaults for streaming heuristics.
            {"name": "ema", "params": {"window": 50}},
            {"name": "rsi", "params": {"window": 14}},
        ]
    iterator = streaming_service.stream_analysis(symbol, timeframe, indicator_specs)
    return StreamingResponse(iterator, media_type="text/event-stream")
