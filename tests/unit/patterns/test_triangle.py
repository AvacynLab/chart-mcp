"""Tests for triangle detection."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.patterns import PatternsService


def test_triangle_detection():
    highs = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9]
    lows = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    closes = [(high + low) / 2 for high, low in zip(highs, lows, strict=True)]
    frame = pd.DataFrame(
        {
            "ts": list(range(len(closes))),
            "o": closes,
            "h": highs,
            "l": lows,
            "c": closes,
            "v": [100] * len(closes),
        }
    )
    service = PatternsService()
    patterns = service.detect(frame)
    triangles = [p for p in patterns if p.name == "triangle"]
    assert triangles, "Converging highs/lows should trigger a triangle detection"
    assert all(0.3 <= p.confidence <= 0.8 for p in triangles)
