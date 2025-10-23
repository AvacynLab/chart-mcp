"""Tests for moving averages."""

from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, exponential_moving_average, simple_moving_average


def test_simple_moving_average():
    data = pd.DataFrame({"c": [1, 2, 3, 4, 5], "ts": [1, 2, 3, 4, 5]})
    result = simple_moving_average(data, 3)
    assert result.iloc[-1] == pytest.approx(4)


def test_exponential_moving_average():
    data = pd.DataFrame({"c": [10, 11, 12, 13, 14], "ts": [1, 2, 3, 4, 5]})
    result = exponential_moving_average(data, 3)
    assert result.iloc[-1] == pytest.approx(13.06, abs=0.01)


def test_indicator_service_ma():
    frame = pd.DataFrame({"ts": [1, 2, 3, 4, 5], "o": [0] * 5, "h": [0] * 5, "l": [0] * 5, "c": [1, 2, 3, 4, 5], "v": [0] * 5})
    service = IndicatorService()
    result = service.compute(frame, "ma", {"window": 3})
    assert round(result.dropna().iloc[-1]["ma"], 2) == 4.0
