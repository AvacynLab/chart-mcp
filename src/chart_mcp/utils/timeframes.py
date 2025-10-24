"""Utilities for parsing and mapping timeframe strings."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict

from chart_mcp.utils.errors import BadRequest

_TIMEFRAME_TO_SECONDS: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


def parse_timeframe(value: str) -> int:
    """Convert timeframe string to seconds, raising BadRequest if invalid."""
    try:
        return _TIMEFRAME_TO_SECONDS[value]
    except KeyError as exc:
        raise BadRequest(f"Unsupported timeframe '{value}'") from exc


def to_timedelta(value: str) -> timedelta:
    """Return a timedelta representing the timeframe duration."""
    return timedelta(seconds=parse_timeframe(value))


def ccxt_timeframe(value: str) -> str:
    """Return CCXT compatible timeframe string."""
    parse_timeframe(value)  # validate
    return value


SUPPORTED_TIMEFRAMES = tuple(_TIMEFRAME_TO_SECONDS.keys())
