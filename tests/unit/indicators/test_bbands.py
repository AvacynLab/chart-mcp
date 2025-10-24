"""Tests for Bollinger Bands indicator."""
from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, bollinger_bands
from chart_mcp.utils.errors import BadRequest


def test_bollinger_columns():
    frame = pd.DataFrame({"c": [float(i) for i in range(1, 40)]})
    result = bollinger_bands(frame, window=5, stddev=2.0)
    assert set(result.columns) == {"middle", "upper", "lower"}


def test_indicator_service_bbands():
    frame = pd.DataFrame({"ts": list(range(40)), "o": [0] * 40, "h": [0] * 40, "l": [0] * 40, "c": list(range(40)), "v": [0] * 40})
    service = IndicatorService()
    data = service.compute(frame, "bbands", {"window": 5})
    assert not data.dropna().empty


def test_bollinger_invalid_params():
    """Bollinger Bands validation covers window and stddev arguments."""

    frame = pd.DataFrame({"c": [float(i) for i in range(1, 10)]})
    with pytest.raises(BadRequest):
        bollinger_bands(frame, window=0)
    with pytest.raises(BadRequest):
        bollinger_bands(frame, window=5, stddev=0.0)
