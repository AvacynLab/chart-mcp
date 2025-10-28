"""Utilities for parsing and mapping timeframe strings.

The helpers below centralise timeframe validation so the rest of the codebase can
rely on a single source of truth. They normalise user supplied strings, ensure
they map to one of the CCXT-supported intervals and expose helpers returning
seconds and :class:`datetime.timedelta` instances. All validation errors raise a
``422 Unprocessable Entity`` HTTP status so API clients immediately understand
that the payload must be fixed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, Tuple

from chart_mcp.utils.errors import UnprocessableEntity

# The mapping covers the canonical short codes documented by CCXT. We order the
# definitions from the fastest to the slowest interval so consumers iterating
# over ``SUPPORTED_TIMEFRAMES`` see an intuitive progression.
_TIMEFRAME_DEFINITIONS: Tuple[Tuple[str, int], ...] = (
    ("1m", 60),
    ("3m", 180),
    ("5m", 300),
    ("15m", 900),
    ("30m", 1_800),
    ("45m", 2_700),
    ("1h", 3_600),
    ("2h", 7_200),
    ("3h", 10_800),
    ("4h", 14_400),
    ("6h", 21_600),
    ("8h", 28_800),
    ("12h", 43_200),
    ("1d", 86_400),
    ("3d", 259_200),
    ("1w", 604_800),
)

# Derived lookups speed up validation without exposing the internal details.
_TIMEFRAME_TO_SECONDS: Dict[str, int] = {
    alias: seconds for alias, seconds in _TIMEFRAME_DEFINITIONS
}
_NORMALISED_ALIASES: Dict[str, str] = {
    alias.lower(): alias for alias, _ in _TIMEFRAME_DEFINITIONS
}


def _normalise(value: str) -> str:
    """Return the canonical timeframe identifier for ``value``.

    ``CCXT`` expects lowercase suffixes (``m`` for minutes, ``h`` for hours).
    Inputs are therefore trimmed and lower-cased before looking them up in the
    canonical registry. When the provided timeframe is empty or outside the
    supported table we raise :class:`UnprocessableEntity` to signal a semantic
    validation error to the API layer.
    """
    cleaned = value.strip()
    if not cleaned:
        raise UnprocessableEntity("Timeframe cannot be empty")
    lookup_key = cleaned.lower()
    try:
        return _NORMALISED_ALIASES[lookup_key]
    except KeyError as exc:
        raise UnprocessableEntity(f"Unsupported timeframe '{value}'") from exc


def parse_timeframe(value: str) -> int:
    """Convert a timeframe string to seconds, enforcing strict validation."""
    alias = _normalise(value)
    return _TIMEFRAME_TO_SECONDS[alias]


def to_timedelta(value: str) -> timedelta:
    """Return a timedelta representing the timeframe duration."""
    return timedelta(seconds=parse_timeframe(value))


def ccxt_timeframe(value: str) -> str:
    """Return the exact timeframe token expected by CCXT."""
    return _normalise(value)


SUPPORTED_TIMEFRAMES = tuple(alias for alias, _ in _TIMEFRAME_DEFINITIONS)
