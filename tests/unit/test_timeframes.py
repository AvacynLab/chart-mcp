"""Tests for timeframe utilities."""

from __future__ import annotations

import pytest

from chart_mcp.utils.errors import UnprocessableEntity
from chart_mcp.utils.timeframes import (
    SUPPORTED_TIMEFRAMES,
    ccxt_timeframe,
    parse_timeframe,
    to_timedelta,
)


def test_parse_timeframe_valid():
    for tf in SUPPORTED_TIMEFRAMES:
        seconds = parse_timeframe(tf)
        assert seconds > 0
        assert to_timedelta(tf).total_seconds() == seconds


def test_parse_timeframe_invalid():
    """Invalid codes must raise a 422-compatible error type."""
    with pytest.raises(UnprocessableEntity):
        parse_timeframe("2x")


def test_ccxt_timeframe_roundtrip():
    """`ccxt_timeframe` should normalise case and whitespace."""
    assert ccxt_timeframe("1h") == "1h"
    assert ccxt_timeframe(" 1H ") == "1h"


def test_parse_timeframe_strips_whitespace_and_case() -> None:
    """Whitespace or uppercase suffixes are tolerated but normalised."""
    assert parse_timeframe(" 5M ") == 300
