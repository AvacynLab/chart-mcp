"""Regression coverage for head & shoulders pattern heuristics."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from chart_mcp.services.patterns import PatternResult, PatternsService


def _build_frame(*, closes: Iterable[float], highs: Iterable[float], lows: Iterable[float]) -> pd.DataFrame:
    """Return a fully populated OHLCV dataframe for deterministic tests."""
    closes_list = list(closes)
    highs_list = list(highs)
    lows_list = list(lows)
    assert len(closes_list) == len(highs_list) == len(lows_list)
    length = len(closes_list)
    return pd.DataFrame(
        {
            "ts": list(range(length)),
            "o": closes_list,
            "h": highs_list,
            "l": lows_list,
            "c": closes_list,
            "v": [1_000] * length,
        }
    )


def _pick_metadata(result: PatternResult) -> dict[str, object]:
    """Convenience accessor returning a shallow copy of the metadata."""
    return dict(result.metadata)


def test_detects_bearish_head_shoulders() -> None:
    """Bearish formations built from swing highs should be detected reliably."""
    closes = [
        100.0,
        103.5,
        109.0,
        104.0,
        111.0,
        115.0,
        112.0,
        106.5,
        110.0,
        104.5,
        101.5,
    ]
    highs = [
        101.0,
        104.0,
        109.0,
        105.0,
        112.0,
        115.0,
        112.5,
        107.0,
        110.2,
        105.0,
        102.0,
    ]
    lows = [
        99.0,
        101.0,
        104.5,
        101.2,
        108.0,
        109.5,
        104.8,
        100.0,
        105.2,
        100.5,
        98.5,
    ]
    frame = _build_frame(closes=closes, highs=highs, lows=lows)

    results = PatternsService().detect(frame)
    bearish = [
        result
        for result in results
        if result.metadata.get("type") == "head_shoulders" and result.metadata.get("direction") == "bearish"
    ]
    assert bearish, "Expected at least one bearish head & shoulders candidate"
    pattern = bearish[0]
    metadata = _pick_metadata(pattern)

    assert pattern.name == "head_shoulders"
    assert pattern.score >= 0.6
    assert 0.55 <= pattern.confidence <= 0.9
    indices = metadata["indices"]
    assert indices["iL"] < indices["iHead"] < indices["iR"], "Shoulder ordering must be preserved"
    assert pattern.start_ts == indices["iL"]
    assert pattern.end_ts == indices["iR"]


def test_detects_bullish_inverse_head_shoulders() -> None:
    """Inverse formations built from swing lows should be detected reliably."""
    closes = [
        96.0,
        95.0,
        90.5,
        92.0,
        88.5,
        85.0,
        89.0,
        93.0,
        90.2,
        94.5,
        97.0,
    ]
    highs = [
        97.5,
        98.0,
        102.0,
        99.8,
        101.3,
        98.5,
        101.2,
        103.0,
        102.6,
        105.5,
        107.5,
    ]
    lows = [
        95.0,
        94.0,
        90.0,
        92.0,
        88.0,
        85.0,
        88.5,
        92.5,
        90.0,
        94.0,
        96.0,
    ]
    frame = _build_frame(closes=closes, highs=highs, lows=lows)

    results = PatternsService().detect(frame)
    bullish = [
        result
        for result in results
        if result.metadata.get("type") == "head_shoulders" and result.metadata.get("direction") == "bullish"
    ]
    assert bullish, "Expected at least one inverse head & shoulders candidate"
    pattern = bullish[0]
    metadata = _pick_metadata(pattern)

    assert pattern.name == "inverse_head_shoulders"
    assert pattern.score >= 0.6
    assert 0.55 <= pattern.confidence <= 0.9
    indices = metadata["indices"]
    assert indices["iL"] < indices["iHead"] < indices["iR"], "Shoulder ordering must be preserved"
    assert pattern.start_ts == indices["iL"]
    assert pattern.end_ts == indices["iR"]
