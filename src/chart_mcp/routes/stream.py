"""Streaming route for SSE analysis."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from chart_mcp.routes.auth import require_token
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/stream", tags=["stream"], dependencies=[Depends(require_token)])


def get_streaming_service(request: Request) -> StreamingService:
    return request.app.state.streaming_service


@router.get("/analysis")
async def stream_analysis(
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    indicators: List[str] = Query([], description="Indicator names such as ema,rsi"),
    streaming_service: StreamingService = Depends(get_streaming_service),
) -> StreamingResponse:
    """Stream analysis events using Server-Sent Events."""

    parse_timeframe(timeframe)
    indicator_specs = [{"name": name, "params": {}} for name in indicators] if indicators else [
        {"name": "ema", "params": {"window": 50}},
        {"name": "rsi", "params": {"window": 14}},
    ]
    iterator = streaming_service.stream_analysis(symbol, timeframe, indicator_specs)
    return StreamingResponse(iterator, media_type="text/event-stream")
