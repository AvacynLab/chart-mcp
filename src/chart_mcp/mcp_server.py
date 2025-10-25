"""Registration of MCP tools for chart_mcp services."""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    SupportsFloat,
    cast,
)

import pandas as pd

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider, normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService

# Module-level caches keep lazy behaviour while remaining monkeypatch friendly for tests.
_provider: CcxtDataProvider | None = None
_indicator_service: IndicatorService | None = None
_levels_service: LevelsService | None = None
_patterns_service: PatternsService | None = None
_analysis_service: AnalysisLLMService | None = None


def _get_provider() -> CcxtDataProvider:
    """Instantiate the market data provider lazily to avoid import-time side effects."""
    global _provider
    if _provider is None:
        _provider = CcxtDataProvider()
    return _provider


def _get_indicator_service() -> IndicatorService:
    """Return a cached indicator service instance."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service


def _get_levels_service() -> LevelsService:
    """Return a cached support/resistance detection service."""
    global _levels_service
    if _levels_service is None:
        _levels_service = LevelsService()
    return _levels_service


def _get_patterns_service() -> PatternsService:
    """Return a cached chart pattern detection service."""
    global _patterns_service
    if _patterns_service is None:
        _patterns_service = PatternsService()
    return _patterns_service


def _get_analysis_service() -> AnalysisLLMService:
    """Return a cached analysis summarisation service."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisLLMService()
    return _analysis_service


def _get_crypto_frame(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> pd.DataFrame:
    """Return the raw OHLCV dataframe for internal tool consumption."""
    provider = _get_provider()
    return provider.get_ohlcv(symbol, timeframe, limit=limit, start=start, end=end)


def _serialize_ohlcv(frame: pd.DataFrame) -> List[Dict[str, float | int]]:
    """Convert an OHLCV dataframe into JSON-serialisable dictionaries."""
    records: List[Dict[str, float | int]] = []
    for row in frame.to_dict(orient="records"):
        records.append(
            {
                "ts": int(row["ts"]),
                "o": float(row["o"]),
                "h": float(row["h"]),
                "l": float(row["l"]),
                "c": float(row["c"]),
                "v": float(row["v"]),
            }
        )
    return records


def get_crypto_data(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> List[Dict[str, float | int]]:
    """Expose OHLCV rows as JSON records for MCP tools."""
    frame = _get_crypto_frame(symbol, timeframe, limit=limit, start=start, end=end)
    return _serialize_ohlcv(frame)


def compute_indicator(
    symbol: str,
    timeframe: str,
    indicator: str,
    params: Optional[Dict[str, float]] = None,
    *,
    limit: int = 500,
) -> List[Dict[str, float | int]]:
    """Compute indicator values and emit JSON-serialisable rows."""
    frame = _get_crypto_frame(symbol, timeframe, limit=limit)
    indicator_service = _get_indicator_service()
    indicator_frame = indicator_service.compute(frame, indicator, params or {})
    cleaned = indicator_frame.dropna()
    if cleaned.empty:
        return []
    timestamps = frame.loc[cleaned.index, "ts"].astype(int).tolist()
    result: List[Dict[str, float | int]] = []
    for ts_value, payload in zip(timestamps, cleaned.to_dict(orient="records"), strict=True):
        record: Dict[str, float | int] = {"ts": int(ts_value)}
        for key, value in payload.items():
            record[str(key)] = float(cast(SupportsFloat, value))
        result.append(record)
    return result


def identify_support_resistance(symbol: str, timeframe: str) -> List[Dict[str, object]]:
    """Detect support/resistance levels for MCP tool."""
    frame = _get_crypto_frame(symbol, timeframe)
    levels_service = _get_levels_service()
    levels = levels_service.detect_levels(frame)
    return [
        {
            "price": float(lvl.price),
            "kind": lvl.kind,
            "strength": float(lvl.strength),
            "ts_range": {
                "start_ts": int(lvl.ts_range[0]),
                "end_ts": int(lvl.ts_range[1]),
            },
        }
        for lvl in levels
    ]


def detect_chart_patterns(symbol: str, timeframe: str) -> List[Dict[str, object]]:
    """Detect chart patterns for MCP tool."""
    frame = _get_crypto_frame(symbol, timeframe)
    patterns_service = _get_patterns_service()
    patterns = patterns_service.detect(frame)
    return [
        {
            "name": pat.name,
            "score": float(pat.score),
            "confidence": float(pat.confidence),
            "start_ts": int(pat.start_ts),
            "end_ts": int(pat.end_ts),
            "points": [{"ts": int(ts), "price": float(price)} for ts, price in pat.points],
        }
        for pat in patterns
    ]


def generate_analysis_summary(
    symbol: str,
    timeframe: str,
    indicators: Iterable[Dict[str, object]] | None = None,
    include_levels: bool = True,
    include_patterns: bool = True,
) -> Dict[str, str]:
    """Generate heuristic analysis summary for MCP tool."""
    frame = _get_crypto_frame(symbol, timeframe)
    indicator_specs: Iterable[Dict[str, object]] = indicators or [
        # Provide sensible defaults to guarantee coverage for summary heuristics.
        {"name": "ema", "params": {"window": 50}},
        {"name": "rsi", "params": {"window": 14}},
    ]
    highlights: Dict[str, float] = {}
    for spec in indicator_specs:
        name_obj = spec.get("name")
        params_raw = spec.get("params", {})
        name = str(name_obj) if name_obj is not None else "unknown"
        params_mapping: Mapping[str, object] = params_raw if isinstance(params_raw, Mapping) else {}
        params = {
            str(key): float(cast(SupportsFloat, value)) for key, value in params_mapping.items()
        }
        indicator_service = _get_indicator_service()
        data = indicator_service.compute(frame, name, params)
        cleaned = data.dropna()
        if cleaned.empty:
            continue
        latest = cleaned.iloc[-1]
        first_value_raw = next(iter(latest.values), 0.0)
        first_value = float(cast(SupportsFloat, first_value_raw))
        highlights[name] = first_value
    levels_service = _get_levels_service()
    patterns_service = _get_patterns_service()
    levels = levels_service.detect_levels(frame) if include_levels else []
    patterns = patterns_service.detect(frame) if include_patterns else []
    normalized_symbol = normalize_symbol(symbol)
    analysis_service = _get_analysis_service()
    summary_result = analysis_service.summarize(
        normalized_symbol, timeframe, highlights, levels, patterns
    )
    return {
        "summary": summary_result.summary,
        "disclaimer": summary_result.disclaimer,
    }


__all__ = [
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
]


class _ToolRegistrar(Protocol):
    """Typing contract for MCP servers capable of registering tools."""

    def tool(
        self,
        name_or_fn: Callable[..., Any] | str | None = None,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Any]:
        """Return a decorator registering *name* against the provided callable."""


def register_tools(registrar: _ToolRegistrar) -> None:
    """Attach all chart MCP tools to *registrar* under stable identifiers."""
    registrar.tool("get_crypto_data")(get_crypto_data)
    registrar.tool("compute_indicator")(compute_indicator)
    registrar.tool("identify_support_resistance")(identify_support_resistance)
    registrar.tool("detect_chart_patterns")(detect_chart_patterns)
    registrar.tool("generate_analysis_summary")(generate_analysis_summary)


__all__.append("register_tools")
