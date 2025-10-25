"""Tests for Bollinger Bands indicator."""
from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, bollinger_bands
from chart_mcp.utils.errors import BadRequest


def test_bollinger_columns():
    """The helper should expose middle/upper/lower series."""
    frame = pd.DataFrame({"c": [float(i) for i in range(1, 40)]})
    result = bollinger_bands(frame, window=5, stddev=2.0)
    assert set(result.columns) == {"middle", "upper", "lower"}


def test_bollinger_nan_prefix_and_width():
    """Warmup rows should be NaN and stddev should scale the band width."""
    frame = pd.DataFrame({"c": [float(i) for i in range(1, 40)]})
    narrow = bollinger_bands(frame, window=5, stddev=1.0)
    wide = bollinger_bands(frame, window=5, stddev=3.0)
    assert narrow.iloc[:4].isna().all().all()
    assert wide.iloc[:4].isna().all().all()
    # Wider stddev should enlarge the distance between upper and lower bands.
    narrow_width = (narrow["upper"] - narrow["lower"]).iloc[-1]
    wide_width = (wide["upper"] - wide["lower"]).iloc[-1]
    assert wide_width > narrow_width


def test_indicator_service_bbands():
    """Service wrapper should preserve NaNs before enough data is collected."""
    frame = pd.DataFrame(
        {
            "ts": list(range(40)),
            "o": [0] * 40,
            "h": [0] * 40,
            "l": [0] * 40,
            "c": list(range(40)),
            "v": [0] * 40,
        }
    )
    service = IndicatorService()
    data = service.compute(frame, "bbands", {"window": 5, "stddev": 2})
    assert data.iloc[:4].isna().all().all()
    assert not data.dropna().empty


def test_bollinger_invalid_params():
    """Bollinger Bands validation covers window and stddev arguments."""
    frame = pd.DataFrame({"c": [float(i) for i in range(1, 10)]})
    with pytest.raises(BadRequest):
        bollinger_bands(frame, window=0)
    with pytest.raises(BadRequest):
        bollinger_bands(frame, window=5, stddev=0.0)
