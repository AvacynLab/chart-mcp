"""Tests for RSI indicator computations."""
import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, relative_strength_index
from chart_mcp.utils.errors import BadRequest


def test_rsi_flat_series():
    """Flat price series should result in a neutral RSI of ~50."""
    frame = pd.DataFrame({"c": [50, 50, 50, 50, 50, 50, 50]})
    rsi = relative_strength_index(frame, 3)
    assert rsi.iloc[-1] == pytest.approx(50)


def test_rsi_warmup_contains_defaults():
    """Before enough candles accumulate, the RSI falls back to the neutral value."""
    frame = pd.DataFrame({"c": list(range(1, 10))})
    rsi = relative_strength_index(frame, 5)
    assert list(rsi.iloc[:4]) == pytest.approx([50, 50, 50, 50])


def test_indicator_service_rsi():
    """IndicatorService should surface RSI data keyed by 'rsi'."""
    frame = pd.DataFrame({"ts": list(range(10)), "o": [0] * 10, "h": [0] * 10, "l": [0] * 10, "c": list(range(10)), "v": [0] * 10})
    service = IndicatorService()
    data = service.compute(frame, "rsi", {"window": 3})
    assert "rsi" in data.columns
    assert list(data.iloc[:2]["rsi"]) == pytest.approx([50, 50])


def test_rsi_invalid_window_values():
    """RSI should guard against too-small windows and missing history."""
    frame = pd.DataFrame({"c": [60.0, 61.0, 62.0]})
    with pytest.raises(BadRequest):
        relative_strength_index(frame, 0)
    with pytest.raises(BadRequest):
        relative_strength_index(frame, 1)
    with pytest.raises(BadRequest):
        relative_strength_index(frame, 10)
