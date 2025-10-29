"""Unit tests covering timeframe parsing utilities."""

from __future__ import annotations

import pytest

from chart_mcp.utils.errors import UnprocessableEntity
from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES, ccxt_timeframe, parse_timeframe


@pytest.mark.parametrize(
    ("alias", "expected_seconds"),
    [("1m", 60), ("15m", 900), ("1h", 3600), ("1d", 86_400)],
)
def test_parse_timeframe_returns_seconds(alias: str, expected_seconds: int) -> None:
    """Every canonical alias should map to a deterministic second duration."""
    assert parse_timeframe(alias) == expected_seconds


def test_parse_timeframe_rejects_unknown_value() -> None:
    """Invalid inputs must raise ``UnprocessableEntity`` so the API replies 422."""
    with pytest.raises(UnprocessableEntity):
        parse_timeframe("7x")


def test_ccxt_timeframe_matches_supported_aliases() -> None:
    """The CCXT helper should return lowercase aliases from the supported list."""
    for alias in SUPPORTED_TIMEFRAMES:
        assert ccxt_timeframe(alias.upper()) == alias
