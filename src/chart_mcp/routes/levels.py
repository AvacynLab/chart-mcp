"""Routes returning support and resistance levels."""

from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.levels import Level, LevelRange, LevelsResponse
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
    max_levels: int = Query(
        10,
        alias="max",
        ge=1,
        le=100,
        description=("Nombre maximum de niveaux renvoyés (alias 'max' conservé pour les tests)."),
    ),
    services: tuple[MarketDataProvider, LevelsService] = Depends(get_services),
) -> LevelsResponse:
    """Compute supports and resistances for a symbol."""
    provider, service = services
    parse_timeframe(timeframe)
    normalized_symbol = normalize_symbol(symbol)
    frame = provider.get_ohlcv(normalized_symbol, timeframe, limit=limit)
    candidates = service.detect_levels(frame, max_levels=max_levels)
    sorted_candidates = sorted(
        candidates,
        key=lambda lvl: lvl.strength,
        reverse=True,
    )[:max_levels]
    levels = [
        Level(
            kind=cast(Literal["support", "resistance"], candidate.kind),
            price=float(candidate.price),
            strength=float(candidate.strength),
            ts_range=LevelRange(
                start_ts=int(candidate.ts_range[0]),
                end_ts=int(candidate.ts_range[1]),
            ),
        )
        for candidate in sorted_candidates
    ]
    # CCXT expose l'identifiant de l'exchange via ``client.id`` ; nous conservons
    # cette information pour remonter la provenance des niveaux calculés.
    raw_source = getattr(getattr(provider, "client", None), "id", None)
    source = str(raw_source) if raw_source else "custom"
    return LevelsResponse(
        symbol=normalized_symbol,
        timeframe=timeframe,
        source=source,
        levels=levels,
    )
