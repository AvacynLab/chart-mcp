"""Routes orchestrating complete market analysis."""

from __future__ import annotations

from typing import Annotated, Dict, List, Tuple, cast

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    IndicatorSnapshot,
    RequestedIndicator,
)
from chart_mcp.schemas.levels import Level, LevelRange
from chart_mcp.schemas.patterns import Pattern, PatternPoint
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.utils.errors import BadRequest, UnprocessableEntity
from chart_mcp.utils.logging import set_request_metadata
from chart_mcp.utils.timeframes import parse_timeframe

ServicesTuple = Tuple[
    MarketDataProvider, IndicatorService, LevelsService, PatternsService, AnalysisLLMService
]

router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["analysis"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_services(
    request: Request,
) -> ServicesTuple:
    """Retrieve core services from the FastAPI application state."""
    app_state = request.app.state
    return (
        cast(MarketDataProvider, app_state.provider),
        cast(IndicatorService, app_state.indicator_service),
        cast(LevelsService, app_state.levels_service),
        cast(PatternsService, app_state.patterns_service),
        cast(AnalysisLLMService, app_state.analysis_service),
    )


ServiceDeps = Annotated[ServicesTuple, Depends(get_services)]


@router.post(
    "/summary",
    response_model=AnalysisResponse,
    summary="Generate a comprehensive market analysis",
    description=(
        "Combine indicateurs, niveaux et figures chartistes pour produire une synthèse "
        "pédagogique accompagnée d'un disclaimer."
    ),
    response_description="Analyse agrégée prête à être affichée côté front.",
)
def summary(
    payload: AnalysisRequest,
    services: ServiceDeps,
) -> AnalysisResponse:
    """Run the complete analysis pipeline and return the aggregated output."""
    provider, indicator_service, levels_service, patterns_service, analysis_service = services
    try:
        parse_timeframe(payload.timeframe)
    except UnprocessableEntity as exc:
        # Convert semantic validation errors to a 400 so the response stays
        # consistent with the historical behaviour exercised by integration tests.
        raise BadRequest(str(exc)) from exc
    normalized_symbol = normalize_symbol(payload.symbol)
    # Normalise the symbol once and reuse it for provider calls and the
    # downstream summary to guarantee consistent casing/slash formatting.
    set_request_metadata(symbol=normalized_symbol, timeframe=payload.timeframe)
    frame = provider.get_ohlcv(normalized_symbol, payload.timeframe, limit=500)
    if len(frame) < 400:
        # The downstream indicator computations (e.g. Bollinger 200) require a
        # sizeable history window. Enforce a consistent floor so API responses
        # remain predictable across providers with limited market data.
        raise BadRequest("Analysis requires at least 400 OHLCV rows")
    if payload.indicators:
        requested: List[RequestedIndicator] = payload.indicators
    else:
        requested = [
            RequestedIndicator(name="ema", params={"window": 50}),
            RequestedIndicator(name="rsi", params={"window": 14}),
        ]
    indicator_snapshots: List[IndicatorSnapshot] = []
    indicator_highlights: Dict[str, float] = {}
    for spec in requested:
        data = indicator_service.compute(frame, spec.name, spec.params)
        cleaned = data.dropna()
        if cleaned.empty:
            continue
        latest_row = cleaned.iloc[-1]
        latest_values = {str(k): float(v) for k, v in latest_row.items()}
        indicator_snapshots.append(IndicatorSnapshot(name=spec.name, latest=latest_values))
        first_value = next(iter(latest_values.values()), 0.0)
        indicator_highlights[spec.name] = float(first_value)
    levels = levels_service.detect_levels(frame) if payload.include_levels else []
    level_models = (
        [
            Level(
                kind=lvl.kind,
                price=float(lvl.price),
                strength=float(lvl.strength),
                ts_range=LevelRange(
                    start_ts=int(lvl.ts_range[0]),
                    end_ts=int(lvl.ts_range[1]),
                ),
                strength_label=lvl.strength_label,
            )
            for lvl in levels
        ]
        if payload.include_levels
        else None
    )
    patterns = patterns_service.detect(frame) if payload.include_patterns else []
    pattern_models = (
        [
            Pattern(
                name=pat.name,
                score=pat.score,
                start_ts=pat.start_ts,
                end_ts=pat.end_ts,
                points=[PatternPoint(ts=ts, price=price) for ts, price in pat.points],
                confidence=pat.confidence,
            )
            for pat in patterns
        ]
        if payload.include_patterns
        else None
    )
    summary_result = analysis_service.summarize(
        normalized_symbol,
        payload.timeframe,
        indicator_highlights,
        levels,
        patterns,
    )
    limits = [
        "Analyse heuristique basée sur données historiques",
        "Pas de recommandation implicite",
    ]
    return AnalysisResponse(
        symbol=normalized_symbol,
        timeframe=payload.timeframe,
        indicators=indicator_snapshots,
        levels=level_models,
        patterns=pattern_models,
        summary=summary_result.summary,
        disclaimer=summary_result.disclaimer,
        limits=limits,
    )
