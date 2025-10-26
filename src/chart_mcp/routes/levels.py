"""Routes returning support and resistance levels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.levels import Level, LevelsResponse
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.services.levels import LevelsService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/levels",
    tags=["levels"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_services(request: Request) -> tuple[MarketDataProvider, LevelsService]:
    """Return provider and levels service from the application state."""
    return request.app.state.provider, request.app.state.levels_service


@router.get("", response_model=LevelsResponse)
def list_levels(
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    limit: int = Query(500, ge=1, le=5000),
    max: int = Query(10, ge=1, le=100, description="Nombre maximum de niveaux renvoyés."),
    services: tuple[MarketDataProvider, LevelsService] = Depends(get_services),
) -> LevelsResponse:
    """Compute supports and resistances for a symbol."""
    provider, service = services
    parse_timeframe(timeframe)
    normalized_symbol = normalize_symbol(symbol)
    frame = provider.get_ohlcv(normalized_symbol, timeframe, limit=limit)
    max_levels = max
    candidates = service.detect_levels(frame, max_levels=max_levels)
    sorted_candidates = sorted(candidates, key=lambda lvl: lvl.strength, reverse=True)[:max_levels]
    levels = [
        Level(
            kind=candidate.kind,
            price=float(candidate.price),
            strength=float(candidate.strength),
            ts_range=(int(candidate.ts_range[0]), int(candidate.ts_range[1])),
        )
        for candidate in sorted_candidates
    ]
    return LevelsResponse(symbol=normalized_symbol, timeframe=timeframe, levels=levels)
