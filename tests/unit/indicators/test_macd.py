"""Tests for MACD indicator."""
from __future__ import annotations

import pandas as pd

from chart_mcp.services.indicators import IndicatorService, macd


def test_macd_structure():
    frame = pd.DataFrame({"c": [i for i in range(1, 60)]})
    result = macd(frame, fast=12, slow=26, signal=9)
    assert set(result.columns) == {"macd", "signal", "hist"}


def test_indicator_service_macd():
    frame = pd.DataFrame({"ts": list(range(60)), "o": [0] * 60, "h": [0] * 60, "l": [0] * 60, "c": list(range(60)), "v": [0] * 60})
    service = IndicatorService()
    data = service.compute(frame, "macd", {})
    assert not data.dropna().empty
