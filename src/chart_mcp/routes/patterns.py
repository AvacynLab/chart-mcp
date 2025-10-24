"""Routes exposing chart pattern detections."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.patterns import Pattern, PatternPoint, PatternsResponse
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.patterns import PatternResult, PatternsService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/patterns",
    tags=["patterns"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_services(request: Request) -> tuple[MarketDataProvider, PatternsService]:
    """Return provider and patterns service from the application state."""
    return request.app.state.provider, request.app.state.patterns_service


@router.get("", response_model=PatternsResponse)
def list_patterns(
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    limit: int = Query(500, ge=50, le=2000),
    services: tuple[MarketDataProvider, PatternsService] = Depends(get_services),
) -> PatternsResponse:
    """Detect chart patterns for the provided symbol/timeframe."""
    provider, service = services
    parse_timeframe(timeframe)
    frame = provider.get_ohlcv(symbol, timeframe, limit=limit)
    detected: List[PatternResult] = service.detect(frame)
    patterns: List[Pattern] = [
        Pattern(
            name=result.name,
            score=result.score,
            start_ts=result.start_ts,
            end_ts=result.end_ts,
            points=[PatternPoint(ts=ts, price=price) for ts, price in result.points],
            confidence=result.confidence,
        )
        for result in detected
    ]
    return PatternsResponse(symbol=symbol.upper(), timeframe=timeframe, patterns=patterns)
