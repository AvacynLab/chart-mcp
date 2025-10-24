"""Tests for double top/bottom detection."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.patterns import PatternsService


def _frame_from_closes(closes: list[float]) -> pd.DataFrame:
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


def test_double_top_detection():
    closes = [10, 12, 14, 16, 18, 16, 14, 18, 16, 14]
    frame = _frame_from_closes(closes)
    service = PatternsService()
    patterns = service.detect(frame)
    assert any(p.name == "double_top" for p in patterns)


def test_double_bottom_detection():
    closes = [10, 8, 6, 7, 6, 7, 9, 11, 10, 9]
    frame = _frame_from_closes(closes)
    service = PatternsService()
    patterns = service.detect(frame)
    assert any(p.name == "double_bottom" for p in patterns)
