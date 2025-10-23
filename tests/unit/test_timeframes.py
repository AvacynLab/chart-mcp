"""Tests for timeframe utilities."""

from __future__ import annotations

import pytest

from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES, ccxt_timeframe, parse_timeframe, to_timedelta
from chart_mcp.utils.errors import BadRequest


def test_parse_timeframe_valid():
    for tf in SUPPORTED_TIMEFRAMES:
        seconds = parse_timeframe(tf)
        assert seconds > 0
        assert to_timedelta(tf).total_seconds() == seconds


def test_parse_timeframe_invalid():
    with pytest.raises(BadRequest):
        parse_timeframe("2x")


def test_ccxt_timeframe_roundtrip():
    assert ccxt_timeframe("1h") == "1h"
