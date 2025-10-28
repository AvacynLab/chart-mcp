"""Regression tests for the technical indicator helpers and service layer."""

from __future__ import annotations

import pandas as pd
import pandas.testing as pdt
import pytest

import chart_mcp.services.indicators as indicators_module
from chart_mcp.services.indicators import (
    IndicatorService,
    bollinger_bands,
    exponential_moving_average,
    macd,
    relative_strength_index,
    simple_moving_average,
)
from chart_mcp.utils.errors import BadRequest


def _build_ohlcv(length: int = 60) -> pd.DataFrame:
    """Return a synthetic OHLCV dataframe with monotonic closes."""
    closes = [float(i) for i in range(1, length + 1)]
    return pd.DataFrame(
        {
            "ts": list(range(length)),
            "o": closes,
            "h": [value + 0.5 for value in closes],
            "l": [value - 0.5 for value in closes],
            "c": closes,
            "v": [1000 + i for i in range(length)],
        }
    )


def test_simple_moving_average_matches_service_output() -> None:
    """The SMA helper and the service wrapper should expose the same series."""
    frame = _build_ohlcv(20)
    window = 5
    helper = simple_moving_average(frame, window)
    service = IndicatorService().compute(frame, "ma", {"window": window})
    assert list(service.columns) == [f"sma_{window}"]
    pdt.assert_series_equal(service[f"sma_{window}"], helper, check_names=True)


def test_indicator_service_accepts_sma_alias() -> None:
    """Both ``ma`` and ``sma`` identifiers should map to the SMA implementation."""
    frame = _build_ohlcv(15)
    window = 3
    service = IndicatorService()
    direct = service.compute(frame, "ma", {"window": window})
    alias = service.compute(frame, "sma", {"window": window})
    pdt.assert_frame_equal(direct, alias)


def test_exponential_moving_average_default_column_naming() -> None:
    """EMA defaults should surface the canonical ``ema_<window>`` column."""
    frame = _build_ohlcv(25)
    service = IndicatorService()
    result = service.compute(frame, "ema", {})
    assert list(result.columns) == [f"ema_{indicators_module.DEFAULT_EMA_WINDOW}"]
    manual = exponential_moving_average(frame, indicators_module.DEFAULT_EMA_WINDOW)
    pdt.assert_series_equal(result.iloc[:, 0], manual, check_names=True)


def test_relative_strength_index_neutral_warmup() -> None:
    """Early RSI values should default to the neutral 50 level."""
    frame = _build_ohlcv(30)
    window = 14
    series = relative_strength_index(frame, window)
    assert series.iloc[: window - 1].eq(50.0).all()
    wrapped = IndicatorService().compute(frame, "rsi", {"window": window})
    assert list(wrapped.columns) == [f"rsi_{window}"]
    pdt.assert_series_equal(wrapped.iloc[:, 0], series, check_names=True)


def test_macd_columns_and_histogram_relationship() -> None:
    """MACD helper should expose explicit column names and match the service."""
    frame = _build_ohlcv(120)
    fast, slow, signal = 12, 26, 9
    helper = macd(frame, fast=fast, slow=slow, signal=signal)
    assert set(helper.columns) == {"macd", "macd_signal", "macd_hist"}
    # Histogram must equal the difference between macd and macd_signal.
    pdt.assert_series_equal(helper["macd"] - helper["macd_signal"], helper["macd_hist"], check_names=False)
    service = IndicatorService().compute(frame, "macd", {"fast": fast, "slow": slow, "signal": signal})
    pdt.assert_frame_equal(helper, service)


def test_bollinger_bands_column_naming_and_scaling() -> None:
    """Bollinger Bands helper exposes ``bb_*`` columns with scalable width."""
    frame = _build_ohlcv(60)
    narrow = bollinger_bands(frame, window=20, stddev=1.0)
    wide = bollinger_bands(frame, window=20, stddev=3.0)
    assert list(narrow.columns) == ["bb_middle", "bb_upper", "bb_lower"]
    assert list(wide.columns) == ["bb_middle", "bb_upper", "bb_lower"]
    # Wider standard deviation should increase the gap between upper and lower bands.
    narrow_width = (narrow["bb_upper"] - narrow["bb_lower"]).iloc[-1]
    wide_width = (wide["bb_upper"] - wide["bb_lower"]).iloc[-1]
    assert wide_width > narrow_width
    service = IndicatorService().compute(frame, "bbands", {"window": 20, "stddev": 1.0})
    pdt.assert_frame_equal(narrow, service)


def test_indicator_service_rejects_unknown_identifier() -> None:
    """Unsupported indicator names should yield a ``BadRequest`` error."""
    frame = _build_ohlcv(10)
    with pytest.raises(BadRequest):
        IndicatorService().compute(frame, "ichimoku", {})


def test_indicator_validation_errors_propagate() -> None:
    """Parameter validation rules should mirror trading platform expectations."""
    frame = _build_ohlcv(5)
    with pytest.raises(BadRequest):
        simple_moving_average(frame, 0)
    with pytest.raises(BadRequest):
        exponential_moving_average(frame, -3)
    with pytest.raises(BadRequest):
        relative_strength_index(frame, 1)
    with pytest.raises(BadRequest):
        macd(frame, fast=10, slow=5, signal=2)
    with pytest.raises(BadRequest):
        bollinger_bands(frame, window=2, stddev=0.0)
