"""Unit tests for the OHLCV data adapter."""

from __future__ import annotations

import math

import pandas as pd

from chart_mcp.utils.data_adapter import normalize_ohlcv_frame


def test_normalize_ohlcv_frame_success():
    """The adapter should convert well-formed rows into ``OhlcvRow`` entries."""
    frame = pd.DataFrame(
        {
            "ts": [1, 2],
            "o": [100, 101.5],
            "h": [105, 102],
            "l": [99.5, 100],
            "c": [104, 101],
            "v": [500, 450],
        }
    )

    rows = normalize_ohlcv_frame(frame)

    assert len(rows) == 2
    assert rows[0].ts == 1
    assert rows[1].close == 101


def test_normalize_ohlcv_frame_skips_invalid_rows():
    """Rows containing ``NaN`` or non numeric values must be skipped."""
    frame = pd.DataFrame(
        {
            "ts": [1, 2, None],
            "o": [100, math.nan, 102],
            "h": [105, 103, 103],
            "l": [99, 98, 99],
            "c": [104, 102, "oops"],
            "v": [500, 450, 470],
        }
    )

    rows = normalize_ohlcv_frame(frame)

    assert len(rows) == 1
    assert rows[0].ts == 1


def test_normalize_ohlcv_frame_missing_columns():
    """If the provider payload lacks the expected columns, nothing is returned."""
    frame = pd.DataFrame({"timestamp": [1, 2], "open": [1, 2]})

    rows = normalize_ohlcv_frame(frame)

    assert rows == []
