"""Routes returning support and resistance levels."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_token
from chart_mcp.schemas.levels import Level, LevelRange, LevelsResponse
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.levels import LevelsService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/api/v1/levels", tags=["levels"], dependencies=[Depends(require_token)])


def get_services(request: Request) -> tuple[MarketDataProvider, LevelsService]:
    """Return provider and levels service from the application state."""
    return request.app.state.provider, request.app.state.levels_service


@router.get("", response_model=LevelsResponse)
def list_levels(
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    limit: int = Query(500, ge=50, le=2000),
    services: tuple[MarketDataProvider, LevelsService] = Depends(get_services),
) -> LevelsResponse:
    """Compute supports and resistances for a symbol."""
    provider, service = services
    parse_timeframe(timeframe)
    frame = provider.get_ohlcv(symbol, timeframe, limit=limit)
    candidates = service.detect_levels(frame)
    levels: List[Level] = [
        Level(
            price=candidate.price,
            strength=candidate.strength,
            kind=candidate.kind,
            ts_range=LevelRange(start_ts=candidate.ts_range[0], end_ts=candidate.ts_range[1]),
        )
        for candidate in candidates
    ]
    return LevelsResponse(symbol=symbol.upper(), timeframe=timeframe, levels=levels)
