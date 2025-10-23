"""Routes orchestrating complete market analysis."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_token
from chart_mcp.schemas.analysis import AnalysisRequest, AnalysisResponse, IndicatorSnapshot
from chart_mcp.schemas.levels import Level, LevelRange
from chart_mcp.schemas.patterns import Pattern, PatternPoint
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"], dependencies=[Depends(require_token)])


def get_services(
    request: Request,
) -> tuple[MarketDataProvider, IndicatorService, LevelsService, PatternsService, AnalysisLLMService]:
    app = request.app.state
    return (
        app.provider,
        app.indicator_service,
        app.levels_service,
        app.patterns_service,
        app.analysis_service,
    )


@router.post("/summary", response_model=AnalysisResponse)
def summary(
    payload: AnalysisRequest,
    services: tuple[MarketDataProvider, IndicatorService, LevelsService, PatternsService, AnalysisLLMService] = Depends(
        get_services
    ),
) -> AnalysisResponse:
    """Run the complete analysis pipeline and return the aggregated output."""

    provider, indicator_service, levels_service, patterns_service, analysis_service = services
    parse_timeframe(payload.timeframe)
    frame = provider.get_ohlcv(payload.symbol, payload.timeframe, limit=500)
    requested = payload.indicators or [
        {"name": "ema", "params": {"window": 50}},
        {"name": "rsi", "params": {"window": 14}},
    ]
    indicator_snapshots: List[IndicatorSnapshot] = []
    indicator_highlights = {}
    for spec in requested:
        name = spec.name if hasattr(spec, "name") else spec["name"]
        params = spec.params if hasattr(spec, "params") else spec.get("params", {})
        data = indicator_service.compute(frame, name, params)
        cleaned = data.dropna()
        if cleaned.empty:
            continue
        latest_row = cleaned.iloc[-1]
        latest_values = {k: float(v) for k, v in latest_row.items()}
        indicator_snapshots.append(IndicatorSnapshot(name=name, latest=latest_values))
        indicator_highlights[name] = list(latest_values.values())[0]
    levels = levels_service.detect_levels(frame) if payload.include_levels else []
    level_models = [
        Level(
            price=lvl.price,
            strength=lvl.strength,
            kind=lvl.kind,
            ts_range=LevelRange(start_ts=lvl.ts_range[0], end_ts=lvl.ts_range[1]),
        )
        for lvl in levels
    ] if payload.include_levels else None
    patterns = patterns_service.detect(frame) if payload.include_patterns else []
    pattern_models = [
        Pattern(
            name=pat.name,
            score=pat.score,
            start_ts=pat.start_ts,
            end_ts=pat.end_ts,
            points=[PatternPoint(ts=ts, price=price) for ts, price in pat.points],
            confidence=pat.confidence,
        )
        for pat in patterns
    ] if payload.include_patterns else None
    summary_text = analysis_service.summarize(
        payload.symbol,
        payload.timeframe,
        indicator_highlights,
        levels,
        patterns,
    )
    limits = ["Analyse heuristique basée sur données historiques", "Pas de recommandation implicite"]
    return AnalysisResponse(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        indicators=indicator_snapshots,
        levels=level_models,
        patterns=pattern_models,
        summary=summary_text,
        limits=limits,
    )
