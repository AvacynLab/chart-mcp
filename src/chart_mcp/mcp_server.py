from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, SupportsFloat, cast

import pandas as pd

from chart_mcp.config import settings
from chart_mcp.schemas.mcp import (
    MCPAnalysisPayload,
    MCPAnalysisResponse,
    MCPIndicatorRequest,
    MCPLevelPayload,
    MCPLevelsParams,
    MCPLevelsRequest,
    MCPOhlcvPoint,
    MCPPatternPayload,
    MCPPatternsParams,
    MCPPatternsRequest,
    MCPWebSearchRequest,
    MCPWebSearchResponse,
    MCPWebSearchResult,
    MCPWindowedQuery,
    coerce_mapping,
    flatten_indicator_records,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider, normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.services.search import SearchClientProtocol, SearxNGClient
from chart_mcp.utils.errors import UpstreamError

# Lazily instantiated singletons keep the MCP entrypoint lightweight while still allowing
# the test-suite to monkeypatch individual services.
_provider: CcxtDataProvider | None = None
_indicator_service: IndicatorService | None = None
_levels_service: LevelsService | None = None
_patterns_service: PatternsService | None = None
_analysis_service: AnalysisLLMService | None = None
_search_client: SearchClientProtocol | None = None


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


def _get_search_client() -> SearchClientProtocol:
    """Return the configured SearxNG search client for MCP tools."""
    global _search_client
    if _search_client is not None:
        return _search_client
    if not settings.searxng_enabled or not settings.searxng_base_url:
        raise RuntimeError(
            "SearxNG integration is disabled. Configure SEARXNG_BASE_URL to use the web_search tool.",
        )
    _search_client = SearxNGClient(settings.searxng_base_url, timeout=settings.searxng_timeout)
    return _search_client


def _fetch_frame(query: MCPWindowedQuery) -> pd.DataFrame:
    """Fetch and normalise OHLCV data for downstream tools."""
    provider = _get_provider()
    return provider.get_ohlcv(
        query.symbol,
        query.timeframe,
        limit=query.limit,
        start=query.start,
        end=query.end,
    )


def _serialize_ohlcv(frame: pd.DataFrame) -> List[Dict[str, float | int]]:
    """Convert a pandas dataframe into JSON-serialisable dictionaries."""
    payload: List[Dict[str, float | int]] = []
    for row in frame.to_dict(orient="records"):
        point = MCPOhlcvPoint(
            ts=int(row["ts"]),
            o=float(row["o"]),
            h=float(row["h"]),
            l=float(row["l"]),
            c=float(row["c"]),
            v=float(row["v"]),
        )
        payload.append(point.model_dump())
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
    query = MCPWindowedQuery(symbol=symbol, timeframe=timeframe, limit=limit, start=start, end=end)
    frame = _fetch_frame(query)
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
    request = MCPIndicatorRequest(
        symbol=symbol,
        timeframe=timeframe,
        indicator=indicator,
        params=params or {},
        limit=limit,
    )
    frame = _fetch_frame(request)
    indicator_service = _get_indicator_service()
    indicator_frame = indicator_service.compute(frame, request.indicator, request.params)
    cleaned = indicator_frame.dropna()
    if cleaned.empty:
        return []

    timestamps = frame.loc[cleaned.index, "ts"].astype(int).tolist()
    raw_records: List[Dict[str, float | int]] = []
    for ts_value, payload in zip(timestamps, cleaned.to_dict(orient="records"), strict=True):
        raw_records.append(
            {
                "ts": int(ts_value),
                **{str(key): float(cast(SupportsFloat, value)) for key, value in payload.items()},
            }
        )
    return flatten_indicator_records(raw_records)


def identify_support_resistance(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    params: Optional[Mapping[str, SupportsFloat | int]] = None,
) -> List[Dict[str, object]]:
    """Detect support and resistance levels for the requested market.

    Parameters
    ----------
    symbol:
        Trading pair analysed by the tool.
    timeframe:
        Time interval for the OHLCV series (``1m``, ``1h`` …).
    limit:
        Maximum number of candles fetched before running the detector.
    params:
        Optional tuning dictionary mirroring the FastAPI route parameters
        (``max_levels``, ``distance``, ``prominence``, ``merge_threshold``,
        ``min_touches``). Values are validated through
        :class:`~chart_mcp.schemas.mcp.MCPLevelsRequest` to keep the stdio
        contract aligned with the REST API.

    """
    request = MCPLevelsRequest(symbol=symbol, timeframe=timeframe, limit=limit, params=params)
    frame = _fetch_frame(request)
    levels_service = _get_levels_service()
    params_obj = request.params or MCPLevelsParams()
    detection_kwargs = {
        "max_levels": params_obj.max_levels if params_obj.max_levels is not None else 10,
        "distance": params_obj.distance,
        "prominence": params_obj.prominence,
        "merge_threshold": params_obj.merge_threshold or 0.0025,
        "min_touches": params_obj.min_touches or 2,
    }
    levels = levels_service.detect_levels(frame, **detection_kwargs)
    sorted_levels = sorted(levels, key=lambda lvl: lvl.strength, reverse=True)
    if params_obj.max_levels is not None:
        sorted_levels = sorted_levels[: params_obj.max_levels]
    results: List[Dict[str, object]] = []
    for level in sorted_levels:
        payload = MCPLevelPayload(
            price=float(level.price),
            strength=float(level.strength),
            strength_label=level.strength_label,
            kind=level.kind,
            ts_range={"start_ts": int(level.ts_range[0]), "end_ts": int(level.ts_range[1])},
        )
        results.append(payload.model_dump())
    return results


def detect_chart_patterns(
    symbol: str,
    timeframe: str,
    *,
    limit: int = 500,
    params: Optional[Mapping[str, SupportsFloat | int]] = None,
) -> List[Dict[str, object]]:
    """Detect chart patterns and serialise them into plain dictionaries.

    Parameters
    ----------
    symbol:
        Trading pair analysed by the detector.
    timeframe:
        Time interval for the OHLCV series (``1m``, ``4h`` …).
    limit:
        Maximum number of candles fetched before pattern detection.
    params:
        Optional dictionary allowing clients to filter the results using
        ``max_patterns`` and ``min_score``. The configuration is validated via
        :class:`~chart_mcp.schemas.mcp.MCPPatternsRequest` before being applied.

    """
    request = MCPPatternsRequest(symbol=symbol, timeframe=timeframe, limit=limit, params=params)
    frame = _fetch_frame(request)
    patterns_service = _get_patterns_service()
    patterns = patterns_service.detect(frame)
    params_obj = request.params or MCPPatternsParams()
    if params_obj.min_score is not None:
        patterns = [item for item in patterns if item.score >= params_obj.min_score]
    if params_obj.max_patterns is not None:
        patterns = patterns[: params_obj.max_patterns]
    serialized: List[Dict[str, object]] = []
    for pattern in patterns:
        payload = MCPPatternPayload(
            name=pattern.name,
            score=float(pattern.score),
            start_ts=int(pattern.start_ts),
            end_ts=int(pattern.end_ts),
            confidence=float(pattern.confidence),
            points=[{"ts": int(ts), "price": float(price)} for ts, price in pattern.points],
            metadata=pattern.metadata,
        )
        serialized.append(payload.model_dump())
    return serialized


def generate_analysis_summary(
    payload: Mapping[str, object] | None = None,
    timeframe: Optional[str] = None,
    *,
    symbol: Optional[str] = None,
    indicators: Iterable[Mapping[str, object]] | None = None,
    include_levels: Optional[bool] = None,
    include_patterns: Optional[bool] = None,
    limit: int = 500,
) -> Dict[str, object]:
    """Generate a pedagogical natural-language summary for the requested market."""
    request_payload: Mapping[str, object]
    if payload is not None:
        if isinstance(payload, Mapping):
            request_payload = payload
        else:
            if timeframe is None:
                raise ValueError("timeframe must be provided when using legacy signature")
            request_payload = {
                "symbol": str(payload),
                "timeframe": timeframe,
                "limit": limit,
                "indicators": list(indicators or []),
                "include_levels": True if include_levels is None else include_levels,
                "include_patterns": True if include_patterns is None else include_patterns,
            }
    else:
        if symbol is None or timeframe is None:
            raise ValueError("symbol and timeframe must be provided when payload is omitted")
        request_payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "indicators": list(indicators or []),
            "include_levels": True if include_levels is None else include_levels,
            "include_patterns": True if include_patterns is None else include_patterns,
        }
    request = MCPAnalysisPayload.model_validate(request_payload)
    frame = _fetch_frame(request)
    if request.indicators:
        indicator_specs = [spec.model_dump() for spec in request.indicators]
    else:
        indicator_specs = [
            {"name": "ema", "params": {"window": 50}},
            {"name": "rsi", "params": {"window": 14}},
        ]

    indicator_service = _get_indicator_service()
    highlights: Dict[str, float] = {}
    for spec in indicator_specs:
        spec_mapping = coerce_mapping(spec)
        name = str(spec_mapping.get("name", ""))
        params_obj = spec_mapping.get("params")
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

    levels_params = request.levels_params
    level_kwargs = {}
    if levels_params is not None:
        level_kwargs = {
            "max_levels": levels_params.max_levels if levels_params.max_levels is not None else 10,
            "distance": levels_params.distance,
            "prominence": levels_params.prominence,
            "merge_threshold": levels_params.merge_threshold or 0.0025,
            "min_touches": levels_params.min_touches or 2,
        }

    levels = levels_service.detect_levels(frame, **level_kwargs) if request.include_levels else []

    patterns_params = request.patterns_params
    patterns = patterns_service.detect(frame) if request.include_patterns else []
    if request.include_patterns and patterns_params is not None:
        if patterns_params.min_score is not None:
            patterns = [item for item in patterns if item.score >= patterns_params.min_score]
        if patterns_params.max_patterns is not None:
            patterns = patterns[: patterns_params.max_patterns]

    analysis_service = _get_analysis_service()
    normalized_symbol = normalize_symbol(request.symbol)
    summary = analysis_service.summarize(
        normalized_symbol,
        request.timeframe,
        highlights,
        levels,
        patterns,
    )
    response = MCPAnalysisResponse(summary=summary.summary, disclaimer=summary.disclaimer)
    return response.model_dump()


def web_search(
    query: str,
    categories: Iterable[str] | str | None = None,
    time_range: Optional[str] = None,
    *,
    language: str = "fr",
) -> Dict[str, object]:
    """Proxy a search request to SearxNG and normalise the response."""
    request = MCPWebSearchRequest(
        query=query,
        categories=categories,
        time_range=time_range,
        language=language,
    )
    client = _get_search_client()
    try:
        results = client.search(
            query=request.query,
            categories=request.categories,
            time_range=request.time_range,
            language=request.language,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    except UpstreamError as exc:
        raise RuntimeError(f"SearxNG request failed: {exc}") from exc

    payload_results: List[MCPWebSearchResult] = [
        MCPWebSearchResult(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            source=item.source,
            score=float(item.score),
        )
        for item in results
    ]
    response = MCPWebSearchResponse(
        query=request.query,
        categories=request.categories,
        time_range=request.time_range,
        language=request.language,
        results=payload_results,
    )
    return response.model_dump()


__all__ = [
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
    "web_search",
]
