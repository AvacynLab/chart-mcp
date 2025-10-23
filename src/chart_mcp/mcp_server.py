"""Registration of MCP tools for chart_mcp services."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import pandas as pd

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService

_provider = CcxtDataProvider()
_indicator_service = IndicatorService()
_levels_service = LevelsService()
_patterns_service = PatternsService()
_analysis_service = AnalysisLLMService()


def get_crypto_data(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> pd.DataFrame:
    """Return OHLCV data for MCP consumption."""

    return _provider.get_ohlcv(symbol, timeframe, limit=limit, start=start, end=end)


def compute_indicator(symbol: str, timeframe: str, indicator: str, params: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """Compute indicator using shared indicator service."""

    frame = get_crypto_data(symbol, timeframe)
    return _indicator_service.compute(frame, indicator, params or {})


def identify_support_resistance(symbol: str, timeframe: str) -> List[Dict[str, float]]:
    """Detect support/resistance levels for MCP tool."""

    frame = get_crypto_data(symbol, timeframe)
    levels = _levels_service.detect_levels(frame)
    return [
        {"price": lvl.price, "kind": lvl.kind, "strength": lvl.strength, "ts_range": lvl.ts_range}
        for lvl in levels
    ]


def detect_chart_patterns(symbol: str, timeframe: str) -> List[Dict[str, object]]:
    """Detect chart patterns for MCP tool."""

    frame = get_crypto_data(symbol, timeframe)
    patterns = _patterns_service.detect(frame)
    return [
        {
            "name": pat.name,
            "score": pat.score,
            "confidence": pat.confidence,
            "start_ts": pat.start_ts,
            "end_ts": pat.end_ts,
            "points": pat.points,
        }
        for pat in patterns
    ]


def generate_analysis_summary(
    symbol: str,
    timeframe: str,
    indicators: Iterable[Dict[str, object]] | None = None,
    include_levels: bool = True,
    include_patterns: bool = True,
) -> str:
    """Generate heuristic analysis summary for MCP tool."""

    frame = get_crypto_data(symbol, timeframe)
    indicator_specs = indicators or [
        {"name": "ema", "params": {"window": 50}},
        {"name": "rsi", "params": {"window": 14}},
    ]
    highlights: Dict[str, float] = {}
    for spec in indicator_specs:
        name = str(spec.get("name"))
        params = {str(k): float(v) for k, v in dict(spec.get("params", {})).items()}
        data = _indicator_service.compute(frame, name, params)
        cleaned = data.dropna()
        if cleaned.empty:
            continue
        latest = cleaned.iloc[-1]
        highlights[name] = float(list(latest.values)[0])
    levels = _levels_service.detect_levels(frame) if include_levels else []
    patterns = _patterns_service.detect(frame) if include_patterns else []
    return _analysis_service.summarize(symbol, timeframe, highlights, levels, patterns)


__all__ = [
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
]
