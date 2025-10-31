"""Unit tests validating the head and shoulders heuristic.

The scenarios craft synthetic OHLCV data illustrating both bearish and bullish
formations so that the detection service can be asserted deterministically.
Negative data ensures the heuristic does not produce spurious matches.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from chart_mcp.services.patterns import PatternsService


def _build_frame(highs: list[float], lows: list[float]) -> pd.DataFrame:
    """Create a minimal OHLCV dataframe with monotonic timestamps.

    The heuristic primarily consumes ``high`` and ``low`` vectors.  The helper
    therefore mirrors the high prices into the open/close series and keeps a
    flat volume placeholder so that the structure stays easy to reason about.
    """
    timestamps = np.arange(len(highs), dtype=np.int64)
    closes = np.array(highs, dtype=float)
    return pd.DataFrame(
        {
            "ts": timestamps,
            "o": closes,
            "h": np.array(highs, dtype=float),
            "l": np.array(lows, dtype=float),
            "c": closes,
            "v": np.ones_like(closes),
        }
    )


def test_detects_bearish_head_shoulders() -> None:
    """Ensure a classical head & shoulders pattern is detected reliably."""
    # Construct a sequence where peaks at indices 2, 4 and 6 model the
    # left/right shoulders and the head.  The neckline lows at indices 3 and 5
    # are aligned within 1 % to satisfy the flat-neckline rule enforced by the
    # service.
    highs = [95.0, 100.0, 105.0, 101.0, 112.0, 102.0, 104.0, 99.0, 97.0, 96.0]
    lows = [94.0, 98.0, 100.0, 96.0, 101.0, 95.0, 99.0, 94.0, 93.0, 92.0]
    frame = _build_frame(highs, lows)

    service = PatternsService()
    patterns = service.detect(frame)

    # Filter for the bearish head & shoulders entry and validate the qualitative
    # metrics returned by the heuristic.
    hs_matches = [p for p in patterns if p.name == "head_shoulders"]
    assert hs_matches, "Expected at least one bearish head & shoulders pattern"
    match = hs_matches[0]
    assert match.confidence >= 0.6
    assert match.metadata["direction"] == "bearish"

    indices = match.metadata["indices"]
    assert indices["iL"] < indices["iHead"] < indices["iR"]
    assert match.start_ts == frame["ts"].iloc[indices["iL"]]
    assert match.end_ts == frame["ts"].iloc[indices["iR"]]


def test_detects_inverse_head_shoulders() -> None:
    """Validate the inverse (bullish) formation is detected with confidence."""
    # Mirror the previous structure to craft troughs representing an inverse
    # head & shoulders.  Troughs at indices 2, 4 and 6 create the geometry
    # whereas the highs around them offer a balanced neckline.
    lows = [105.0, 101.0, 98.0, 100.0, 95.0, 99.0, 97.0, 101.0, 102.0, 103.0]
    highs = [106.0, 102.0, 99.0, 101.0, 96.0, 100.0, 98.0, 102.0, 103.0, 104.0]
    frame = _build_frame(highs, lows)

    service = PatternsService()
    patterns = service.detect(frame)

    inverse_matches = [p for p in patterns if p.name == "inverse_head_shoulders"]
    assert inverse_matches, "Expected an inverse head & shoulders pattern"
    match = inverse_matches[0]
    assert match.confidence >= 0.6
    assert match.metadata["direction"] == "bullish"

    indices = match.metadata["indices"]
    assert indices["iL"] < indices["iHead"] < indices["iR"]
    assert match.start_ts == frame["ts"].iloc[indices["iL"]]
    assert match.end_ts == frame["ts"].iloc[indices["iR"]]


def test_noise_does_not_produce_false_positive() -> None:
    """Random-like data should not trigger a head & shoulders detection."""
    # Generate a smooth upward trend without the three-peak structure.  The
    # heuristic should therefore return an empty list for head & shoulders
    # patterns to prevent noisy charts from surfacing false positives.
    highs = [float(90 + i) for i in range(12)]
    lows = [price - 1.0 for price in highs]
    frame = _build_frame(highs, lows)

    service = PatternsService()
    patterns = service.detect(frame)

    assert not any(p.name == "head_shoulders" for p in patterns)
    assert not any(p.name == "inverse_head_shoulders" for p in patterns)
