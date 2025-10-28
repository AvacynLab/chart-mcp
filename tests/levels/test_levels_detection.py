"""Integration-style tests for the support/resistance detector."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from chart_mcp.services.levels import LevelCandidate, LevelsService


def _build_frame(closes: Iterable[float]) -> pd.DataFrame:
    """Create a deterministic OHLCV dataframe for the detector."""
    closes_list = list(closes)
    return pd.DataFrame(
        {
            "ts": list(range(len(closes_list))),
            "o": closes_list,
            "h": [price + 0.6 for price in closes_list],
            "l": [price - 0.6 for price in closes_list],
            "c": closes_list,
            "v": [250] * len(closes_list),
        }
    )


def test_detect_levels_scores_and_labels() -> None:
    """Levels with multiple confirmations should be labelled as ``fort``."""
    swing_cycle = [101.0, 103.5, 105.2, 103.4, 101.2, 99.2, 98.1, 99.0, 101.3]
    closes = swing_cycle * 4
    frame = _build_frame(closes)

    service = LevelsService()
    levels = service.detect_levels(frame, max_levels=4, merge_threshold=0.003, min_touches=3)

    assert len(levels) >= 2, "Expect both support and resistance clusters"
    labels = {lvl.strength_label for lvl in levels}
    assert "fort" in labels, "At least one level should receive the strong label"
    for level in levels:
        assert level.strength >= 0.0
        assert level.strength_label in {"fort", "général"}
        assert isinstance(level, LevelCandidate)


def test_merge_threshold_clusters_close_levels() -> None:
    """Increasing the merge threshold should reduce the number of resistance bands."""
    closes = [
        100.0,
        103.0,
        105.0,
        103.1,
        101.0,
        102.2,
        104.6,
        105.1,
        104.8,
        102.0,
        100.2,
        98.4,
        97.9,
        98.5,
        100.7,
        102.9,
        104.9,
        105.3,
        104.7,
        102.1,
    ]
    frame = _build_frame(closes)
    service = LevelsService()

    tight = service.detect_levels(frame, max_levels=6, merge_threshold=0.0008, min_touches=1)
    loose = service.detect_levels(frame, max_levels=6, merge_threshold=0.01, min_touches=1)

    tight_resistances = [lvl for lvl in tight if lvl.kind == "resistance"]
    loose_resistances = [lvl for lvl in loose if lvl.kind == "resistance"]

    assert len(loose_resistances) <= len(tight_resistances)
    assert any(lvl.touches > 1 for lvl in loose_resistances), "Clusters should merge touches"


def test_distance_override_limits_number_of_levels() -> None:
    """Providing a large peak distance should down-sample the detected levels."""
    closes = [
        100.0,
        102.0,
        104.5,
        103.8,
        101.2,
        99.3,
        97.8,
        99.5,
        101.4,
        103.6,
        105.4,
        103.9,
        101.0,
        99.1,
        97.6,
        99.4,
        101.6,
        103.7,
        105.5,
        104.0,
    ]
    frame = _build_frame(closes)
    service = LevelsService()

    default_levels = service.detect_levels(frame, max_levels=10, min_touches=1)
    sparse_levels = service.detect_levels(frame, max_levels=10, distance=6, min_touches=1)

    assert len(sparse_levels) <= len(default_levels)
    assert sparse_levels, "Even with a large distance the detector should return something"
