"""Tests for support and resistance detection."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.levels import LevelsService


def test_levels_detection():
    closes = [10, 12, 15, 13, 11, 9, 11, 13, 15, 14, 12, 10]
    frame = pd.DataFrame(
        {
            "ts": list(range(len(closes))),
            "o": closes,
            "h": [c + 0.5 for c in closes],
            "l": [c - 0.5 for c in closes],
            "c": closes,
            "v": [100] * len(closes),
        }
    )
    service = LevelsService()
    levels = service.detect_levels(frame)
    assert levels
    kinds = {lvl.kind for lvl in levels}
    assert {"support", "resistance"}.issubset(kinds)
