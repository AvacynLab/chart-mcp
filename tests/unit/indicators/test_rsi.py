"""Tests for RSI indicator."""

from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, relative_strength_index


def test_rsi_flat_series():
    frame = pd.DataFrame({"c": [50, 50, 50, 50, 50, 50, 50]})
    rsi = relative_strength_index(frame, 3)
    assert rsi.iloc[-1] == pytest.approx(50)


def test_indicator_service_rsi():
    frame = pd.DataFrame({"ts": list(range(10)), "o": [0] * 10, "h": [0] * 10, "l": [0] * 10, "c": list(range(10)), "v": [0] * 10})
    service = IndicatorService()
    data = service.compute(frame, "rsi", {"window": 3})
    assert "rsi" in data.columns
