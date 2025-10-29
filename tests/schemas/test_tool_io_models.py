"""Regression tests for schema validation used by MCP tools and REST endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from chart_mcp.schemas.analysis import AnalysisResponse, IndicatorSnapshot
from chart_mcp.schemas.common import DatetimeRange
from chart_mcp.schemas.indicators import IndicatorMeta, IndicatorRequest, IndicatorResponse, IndicatorValue
from chart_mcp.schemas.levels import Level, LevelRange
from chart_mcp.schemas.market import MarketDataResponse, OhlcvQuery, OhlcvRow
from chart_mcp.schemas.patterns import Pattern, PatternPoint, PatternsResponse
from chart_mcp.schemas.search import SearchResponse


@pytest.mark.parametrize(
    "raw_indicator,expected_name",
    [("EMA", "ema"), ("rSi", "rsi"), ("macd", "macd")],
)
def test_indicator_request_normalises_identifier(raw_indicator: str, expected_name: str) -> None:
    """Indicator names should be canonicalised and params coerced to floats."""
    request = IndicatorRequest.model_validate(
        {
            "symbol": "btc/usdt",
            "timeframe": "1H",
            "indicator": raw_indicator,
            "params": {"length": "21"},
            "limit": 150,
        }
    )

    assert request.symbol == "BTC/USDT"
    assert request.indicator == expected_name
    assert request.params == {"length": 21.0}


def test_indicator_response_serialises_floats() -> None:
    """Indicator responses must expose float payloads for downstream JSON consumers."""
    response = IndicatorResponse(
        series=[
            IndicatorValue(ts=1, values={"ema": 1}),
            IndicatorValue(ts=2, values={"ema": "1.5"}),
        ],
        meta=IndicatorMeta(symbol="btc/usdt", timeframe="1h", indicator="ema", params={"length": 21}),
    )

    assert response.series[0].values == {"ema": 1.0}
    assert response.series[1].values == {"ema": 1.5}
    assert response.meta.symbol == "BTC/USDT"


def test_level_strength_bounded_between_zero_and_one() -> None:
    """Support/resistance levels enforce a normalised strength score."""
    level = Level(
        price=25_000,
        strength=0.8,
        kind="support",
        ts_range=LevelRange(start_ts=100, end_ts=200),
        strength_label="fort",
    )
    assert level.strength == pytest.approx(0.8)

    with pytest.raises(ValidationError):
        Level(
            price=25_000,
            strength=1.2,
            kind="resistance",
            ts_range=LevelRange(start_ts=100, end_ts=200),
            strength_label="fort",
        )


def test_pattern_confidence_is_normalised() -> None:
    """Patterns reject confidence values outside the [0, 1] interval."""
    Pattern(
        name="head_and_shoulders",
        score=0.72,
        start_ts=10,
        end_ts=40,
        points=[PatternPoint(ts=10, price=1.0), PatternPoint(ts=40, price=0.9)],
        confidence=0.65,
    )

    with pytest.raises(ValidationError):
        Pattern(
            name="channel",
            score=0.5,
            start_ts=10,
            end_ts=40,
            points=[PatternPoint(ts=10, price=1.0), PatternPoint(ts=40, price=0.9)],
            confidence=1.6,
        )


def test_analysis_summary_respects_length_limit() -> None:
    """Analysis summaries are capped to 400 characters as required by the UI contract."""
    AnalysisResponse(
        symbol="BTC/USDT",
        timeframe="1h",
        indicators=[
            IndicatorSnapshot(name="ema", latest={"value": 1.2}),
        ],
        summary="valid",
    )

    too_long = "x" * 401
    with pytest.raises(ValidationError):
        AnalysisResponse(
            symbol="BTC/USDT",
            timeframe="1h",
            indicators=[IndicatorSnapshot(name="ema", latest={"value": 1.2})],
            summary=too_long,
        )


def test_market_query_accepts_datetime_ranges() -> None:
    """Datetime ranges should be converted to integer timestamps when requested."""
    now = datetime.utcnow().replace(microsecond=0)
    query = OhlcvQuery(
        symbol="eth/usdt",
        timeframe="1h",
        range=DatetimeRange(start=now - timedelta(hours=4), end=now),
    )

    assert query.resolved_start() == int((now - timedelta(hours=4)).timestamp())
    assert query.resolved_end() == int(now.timestamp())


def test_market_response_requires_positive_volume() -> None:
    """Market responses reject negative volumes to avoid bogus downstream metrics."""
    MarketDataResponse(
        symbol="ETH/USDT",
        timeframe="1h",
        source="binance",
        rows=[OhlcvRow(ts=1, o=1.0, h=1.1, l=0.9, c=1.05, v=5.0)],
    )

    with pytest.raises(ValidationError):
        MarketDataResponse(
            symbol="ETH/USDT",
            timeframe="1h",
            source="binance",
            rows=[{"ts": 1, "o": 1.0, "h": 1.1, "l": 0.9, "c": 1.05, "v": -5.0}],
        )


def test_search_response_documents_categories() -> None:
    """Search response echoes the categories applied server side."""
    response = SearchResponse(
        query="btc",
        categories=["news", "it"],
        results=[],
    )
    assert response.categories == ["news", "it"]


def test_patterns_response_requires_ordered_points() -> None:
    """Patterns must surface point lists to draw consistent overlays."""
    payload = PatternsResponse(
        symbol="BTC/USDT",
        timeframe="1h",
        source="binance",
        patterns=[
            Pattern(
                name="channel",
                score=0.6,
                start_ts=0,
                end_ts=2,
                points=[PatternPoint(ts=0, price=10.0), PatternPoint(ts=2, price=11.0)],
                confidence=0.6,
            )
        ],
    )

    assert payload.patterns[0].points[0].ts == 0
    assert payload.patterns[0].points[1].ts == 2
