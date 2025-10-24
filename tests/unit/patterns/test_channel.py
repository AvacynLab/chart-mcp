"""Tests for channel detection."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.patterns import PatternsService


def test_channel_detection():
    closes = [i * 1.5 for i in range(40)]
    frame = pd.DataFrame(
        {
            "ts": list(range(len(closes))),
            "o": closes,
            "h": [c + 0.2 for c in closes],
            "l": [c - 0.2 for c in closes],
            "c": closes,
            "v": [50] * len(closes),
        }
    )
    service = PatternsService()
    patterns = service.detect(frame)
    assert any(p.name == "channel" for p in patterns)
