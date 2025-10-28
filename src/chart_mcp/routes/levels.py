"""Routes returning support and resistance levels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.levels import Level, LevelRange, LevelsResponse
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.services.levels import LevelsService
from chart_mcp.utils.logging import set_request_metadata
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/levels",
    tags=["levels"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_services(request: Request) -> tuple[MarketDataProvider, LevelsService]:
    """Return provider and levels service from the application state."""
    return request.app.state.provider, request.app.state.levels_service


@router.get(
    "",
    response_model=LevelsResponse,
    summary="Identify support and resistance levels",
    description=(
        "Analyse une série OHLCV pour détecter les niveaux S/R en regroupant les pics et"
        " en calculant un score de force."
    ),
    response_description="Liste des niveaux classés par force décroissante.",
)
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
    distance: int | None = Query(
        None,
        ge=1,
        le=500,
        description=("Distance minimale entre pics successifs (relai find_peaks)."),
    ),
    prominence: float | None = Query(
        None,
        gt=0.0,
        description=("Prominence minimale des pics (override find_peaks)."),
    ),
    merge_threshold: float = Query(
        0.0025,
        ge=0.0001,
        le=0.05,
        description=(
            "Tolérance relative utilisée pour fusionner des pics proches (0.25% par défaut)."
        ),
    ),
    min_touches: int = Query(
        2,
        ge=1,
        le=10,
        description=("Nombre minimal de contacts pour conserver un niveau."),
    ),
    services: tuple[MarketDataProvider, LevelsService] = Depends(get_services),
) -> LevelsResponse:
    """Compute supports and resistances for a symbol."""
    provider, service = services
    parse_timeframe(timeframe)
    normalized_symbol = normalize_symbol(symbol)
    frame = provider.get_ohlcv(normalized_symbol, timeframe, limit=limit)
    candidates = service.detect_levels(
        frame,
        max_levels=max_levels,
        distance=distance,
        prominence=prominence,
        merge_threshold=merge_threshold,
        min_touches=min_touches,
    )
    sorted_candidates = sorted(
        candidates,
        key=lambda lvl: lvl.strength,
        reverse=True,
    )[:max_levels]
    levels = [
        Level(
            kind=candidate.kind,
            price=float(candidate.price),
            strength=float(candidate.strength),
            strength_label=candidate.strength_label,
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
    # Surface the symbol/timeframe in the logging context for downstream analytics.
    set_request_metadata(symbol=normalized_symbol, timeframe=timeframe)
    return LevelsResponse(
        symbol=normalized_symbol,
        timeframe=timeframe,
        source=source,
        levels=levels,
    )
