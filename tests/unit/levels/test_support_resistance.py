"""Tests for support and resistance detection."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.levels import LevelsService


def _build_frame(closes: list[float]) -> pd.DataFrame:
    """Return a dataframe populated with deterministic OHLCV values."""

    return pd.DataFrame(
        {
            "ts": list(range(len(closes))),
            "o": closes,
            "h": [c + 0.5 for c in closes],
            "l": [c - 0.5 for c in closes],
            "c": closes,
            "v": [100] * len(closes),
        }
    )


def test_levels_detection_returns_support_and_resistance():
    """Baseline detection should yield both support and resistance levels."""

    closes = [10, 12, 15, 13, 11, 9, 11, 13, 15, 14, 12, 10]
    frame = _build_frame(closes)
    service = LevelsService()
    levels = service.detect_levels(frame)

    assert levels, "At least one level is expected for the synthetic swing data"
    kinds = {lvl.kind for lvl in levels}
    assert {"support", "resistance"}.issubset(kinds)


def test_levels_sorted_by_strength_and_truncated():
    """Levels should be sorted by strength and respect the ``max_levels`` bound."""

    closes = [100, 102, 104, 103, 101, 99, 98, 100, 102, 104, 103, 101, 99, 98, 100]
    frame = _build_frame(closes)
    service = LevelsService()

    levels = service.detect_levels(frame, max_levels=3)

    strengths = [lvl.strength for lvl in levels]
    assert strengths == sorted(strengths, reverse=True)
    assert len(levels) <= 3
