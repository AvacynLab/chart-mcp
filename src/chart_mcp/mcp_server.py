from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, SupportsFloat, cast

import pandas as pd

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider, normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService

# Lazily instantiated singletons keep the MCP entrypoint lightweight while still allowing
# the test-suite to monkeypatch individual services.
_provider: CcxtDataProvider | None = None
_indicator_service: IndicatorService | None = None
_levels_service: LevelsService | None = None
_patterns_service: PatternsService | None = None
_analysis_service: AnalysisLLMService | None = None


def _get_provider() -> CcxtDataProvider:
    """Return a cached CCXT-backed market data provider."""
    global _provider
    if _provider is None:
        _provider = CcxtDataProvider()
    return _provider


def _get_indicator_service() -> IndicatorService:
    """Return the indicator computation service."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service


def _get_levels_service() -> LevelsService:
    """Return the support/resistance detection service."""
    global _levels_service
    if _levels_service is None:
        _levels_service = LevelsService()
    return _levels_service


def _get_patterns_service() -> PatternsService:
    """Return the chart pattern detection service."""
    global _patterns_service
    if _patterns_service is None:
        _patterns_service = PatternsService()
    return _patterns_service


def _get_analysis_service() -> AnalysisLLMService:
    """Return the analysis summarisation service."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisLLMService()
    return _analysis_service


def _fetch_frame(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> pd.DataFrame:
    """Fetch and normalise OHLCV data for downstream tools."""
    provider = _get_provider()
    normalized_symbol = normalize_symbol(symbol)
    return provider.get_ohlcv(normalized_symbol, timeframe, limit=limit, start=start, end=end)


def _serialize_ohlcv(frame: pd.DataFrame) -> List[Dict[str, float | int]]:
    """Convert a pandas dataframe into JSON-serialisable dictionaries."""
    payload: List[Dict[str, float | int]] = []
    for row in frame.to_dict(orient="records"):
        payload.append(
            {
                "ts": int(row["ts"]),
                "o": float(row["o"]),
                "h": float(row["h"]),
                "l": float(row["l"]),
                "c": float(row["c"]),
                "v": float(row["v"]),
            }
        )
    return payload


def get_crypto_data(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> List[Dict[str, float | int]]:
    """Return OHLCV rows as JSON objects for MCP clients."""
    frame = _fetch_frame(symbol, timeframe, limit=limit, start=start, end=end)
    return _serialize_ohlcv(frame)


def compute_indicator(
    symbol: str,
    timeframe: str,
    indicator: str,
    params: Optional[Mapping[str, SupportsFloat]] = None,
    *,
    limit: int = 500,
) -> List[Dict[str, float | int]]:
    """Compute a technical indicator and serialise the resulting series."""
    frame = _fetch_frame(symbol, timeframe, limit=limit)
    indicator_service = _get_indicator_service()
    raw_params = {str(key): float(value) for key, value in (params or {}).items()}
    indicator_frame = indicator_service.compute(frame, indicator, raw_params)
    cleaned = indicator_frame.dropna()
    if cleaned.empty:
        return []

    timestamps = frame.loc[cleaned.index, "ts"].astype(int).tolist()
    records: List[Dict[str, float | int]] = []
    for ts_value, payload in zip(timestamps, cleaned.to_dict(orient="records"), strict=True):
        record: Dict[str, float | int] = {"ts": int(ts_value)}
        for key, value in payload.items():
            record[str(key)] = float(cast(SupportsFloat, value))
        records.append(record)
    return records


def identify_support_resistance(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
) -> List[Dict[str, object]]:
    """Detect support and resistance levels for the requested market."""
    frame = _fetch_frame(symbol, timeframe, limit=limit)
    levels_service = _get_levels_service()
    levels = levels_service.detect_levels(frame)
    results: List[Dict[str, object]] = []
    for level in levels:
        results.append(
            {
                "price": float(level.price),
                "strength": float(level.strength),
                "kind": level.kind,
                "ts_range": {
                    "start_ts": int(level.ts_range[0]),
                    "end_ts": int(level.ts_range[1]),
                },
            }
        )
    return results


def detect_chart_patterns(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
) -> List[Dict[str, object]]:
    """Detect chart patterns and serialise them into plain dictionaries."""
    frame = _fetch_frame(symbol, timeframe, limit=limit)
    patterns_service = _get_patterns_service()
    patterns = patterns_service.detect(frame)
    serialized: List[Dict[str, object]] = []
    for pattern in patterns:
        serialized.append(
            {
                "name": pattern.name,
                "score": float(pattern.score),
                "start_ts": int(pattern.start_ts),
                "end_ts": int(pattern.end_ts),
                "confidence": float(pattern.confidence),
                "points": [{"ts": int(ts), "price": float(price)} for ts, price in pattern.points],
            }
        )
    return serialized


def generate_analysis_summary(
    symbol: str,
    timeframe: str,
    *,
    indicators: Iterable[Mapping[str, object]] | None = None,
    include_levels: bool = True,
    include_patterns: bool = True,
) -> Dict[str, object]:
    """Generate a pedagogical natural-language summary for the requested market."""
    frame = _fetch_frame(symbol, timeframe)
    indicator_specs = list(indicators or [])
    if not indicator_specs:
        indicator_specs = [
            {"name": "ema", "params": {"window": 50}},
            {"name": "rsi", "params": {"window": 14}},
        ]

    indicator_service = _get_indicator_service()
    highlights: Dict[str, float] = {}
    for spec in indicator_specs:
        name = str(spec.get("name", ""))
        params_obj = spec.get("params")
        params_map: Mapping[str, object] = params_obj if isinstance(params_obj, Mapping) else {}
        numeric_params = {
            str(key): float(cast(SupportsFloat, value)) for key, value in params_map.items()
        }
        indicator_frame = indicator_service.compute(frame, name, numeric_params)
        cleaned = indicator_frame.dropna()
        if cleaned.empty:
            continue
        latest = cleaned.iloc[-1]
        first_value = next(iter(latest.values), 0.0)
        highlights[name] = float(cast(SupportsFloat, first_value))

    levels_service = _get_levels_service()
    patterns_service = _get_patterns_service()
    levels = levels_service.detect_levels(frame) if include_levels else []
    patterns = patterns_service.detect(frame) if include_patterns else []

    analysis_service = _get_analysis_service()
    normalized_symbol = normalize_symbol(symbol)
    summary = analysis_service.summarize(
        normalized_symbol,
        timeframe,
        highlights,
        levels,
        patterns,
    )
    return {
        "summary": summary.summary,
        "disclaimer": summary.disclaimer,
    }


__all__ = [
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
]
