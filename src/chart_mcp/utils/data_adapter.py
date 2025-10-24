"""Utilities for converting provider payloads into API schemas."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, SupportsFloat, SupportsInt

import pandas as pd

from chart_mcp.schemas.market import OhlcvRow


def _coerce_timestamp(value: object) -> int | None:
    """Attempt to coerce a timestamp value to an integer.

    The helper is intentionally tolerant: any value that cannot be converted to an
    integer (because it is ``None`` or not numeric) returns ``None`` so that the
    caller can decide whether to skip the row. Keeping the coercion logic isolated
    makes the behaviour explicit for the unit tests.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        # ``bool`` subclasses ``int`` so converting explicitly preserves tests that
        # feed sentinel boolean flags.
        return int(value)
    if isinstance(value, SupportsInt):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return int(candidate)
        except ValueError:
            return None
    return None


def _coerce_float(value: object) -> float | None:
    """Convert a raw OHLCV value to ``float`` while rejecting malformed entries."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, SupportsFloat):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            number = float(candidate)
        except ValueError:
            return None
    else:
        return None
    if math.isnan(number):
        return None
    return number


def _coerce_float_series(values: Sequence[object]) -> List[float] | None:
    """Convert the OHLCV series to floats while dropping malformed values.

    ``pandas`` often yields ``numpy`` scalars or ``Decimal`` instances; the
    explicit conversion keeps the API deterministic and ensures that ``NaN``
    values do not propagate to the response. Returning ``None`` instructs the
    caller to skip the row altogether.
    """
    converted: List[float] = []
    for raw in values:
        number = _coerce_float(raw)
        if number is None:
            return None
        converted.append(number)
    return converted


def normalize_ohlcv_frame(frame: pd.DataFrame) -> List[OhlcvRow]:
    """Normalise a provider OHLCV dataframe into a list of ``OhlcvRow``.

    The adapter filters out rows that cannot be converted cleanly (missing
    timestamps or numerical values) so that downstream consumers never receive
    partial or ``NaN``-tainted data. Each row in the dataframe must follow the
    ``(ts, open, high, low, close, volume)`` convention used across the codebase.
    """
    rows: List[OhlcvRow] = []
    columns: Iterable[str] = frame.columns
    expected_columns = {"ts", "o", "h", "l", "c", "v"}
    if not expected_columns.issubset(columns):
        # Defensive guard: providers should expose the canonical schema but tests
        # verify that unexpected shapes simply yield an empty payload.
        return rows

    for ts, open_, high, low, close, volume in frame.itertuples(index=False, name=None):
        timestamp = _coerce_timestamp(ts)
        if timestamp is None:
            continue
        floats = _coerce_float_series((open_, high, low, close, volume))
        if floats is None:
            continue
        open_f, high_f, low_f, close_f, volume_f = floats
        rows.append(
            OhlcvRow(
                ts=timestamp,
                o=open_f,
                h=high_f,
                l=low_f,
                c=close_f,
                v=volume_f,
            )
        )
    return rows


__all__ = ["normalize_ohlcv_frame"]
