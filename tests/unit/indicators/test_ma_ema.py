"""Tests for moving average indicators."""
from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.indicators import (
    IndicatorService,
    exponential_moving_average,
    simple_moving_average,
)
from chart_mcp.utils.errors import BadRequest


def test_simple_moving_average():
    """SMA should match the arithmetic mean over the trailing window."""
    data = pd.DataFrame({"c": [1, 2, 3, 4, 5], "ts": [1, 2, 3, 4, 5]})
    result = simple_moving_average(data, 3)
    assert result.iloc[-1] == pytest.approx(4)


def test_simple_moving_average_nan_prefix():
    """The first ``window - 1`` entries should remain NaN as warmup."""
    data = pd.DataFrame({"c": [1, 2, 3, 4, 5], "ts": [1, 2, 3, 4, 5]})
    result = simple_moving_average(data, 3)
    assert result.iloc[:2].isna().all()


def test_exponential_moving_average():
    """EMA should emphasise recent candles, producing a higher value."""
    data = pd.DataFrame({"c": [10, 11, 12, 13, 14], "ts": [1, 2, 3, 4, 5]})
    result = exponential_moving_average(data, 3)
    assert result.iloc[-1] == pytest.approx(13.06, abs=0.01)


def test_exponential_moving_average_respects_window():
    """Changing the EMA window must impact the smoothing intensity."""
    data = pd.DataFrame({"c": [10, 11, 12, 13, 14, 15], "ts": list(range(6))})
    short = exponential_moving_average(data, 3).iloc[-1]
    long = exponential_moving_average(data, 6).iloc[-1]
    assert short > long


def test_moving_average_invalid_window():
    """Window size must be positive and not exceed the available rows."""
    data = pd.DataFrame({"c": [1.0, 2.0, 3.0]})
    with pytest.raises(BadRequest):
        simple_moving_average(data, 0)
    with pytest.raises(BadRequest):
        simple_moving_average(data, -5)
    with pytest.raises(BadRequest):
        simple_moving_average(data, 10)


def test_indicator_service_ma():
    """IndicatorService delegates to the SMA helper and preserves NaNs."""
    frame = pd.DataFrame({"ts": [1, 2, 3, 4, 5], "o": [0] * 5, "h": [0] * 5, "l": [0] * 5, "c": [1, 2, 3, 4, 5], "v": [0] * 5})
    service = IndicatorService()
    result = service.compute(frame, "ma", {"window": 3})
    assert result.iloc[:2]["ma"].isna().all()
    assert round(result.dropna().iloc[-1]["ma"], 2) == 4.0


def test_indicator_service_ema_respects_params():
    """IndicatorService should pass the provided window to EMA computation."""
    frame = pd.DataFrame(
        {
            "ts": list(range(10)),
            "o": [0] * 10,
            "h": [0] * 10,
            "l": [0] * 10,
            "c": [float(i) for i in range(10)],
            "v": [0] * 10,
        }
    )
    service = IndicatorService()
    ema_fast = service.compute(frame, "ema", {"window": 3}).dropna().iloc[-1]["ema"]
    ema_slow = service.compute(frame, "ema", {"window": 8}).dropna().iloc[-1]["ema"]
    assert ema_fast > ema_slow
