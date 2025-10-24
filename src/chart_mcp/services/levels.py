"""Detection of support and resistance levels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.signal import find_peaks  # type: ignore[import-untyped]


@dataclass
class LevelCandidate:
    """Intermediate structure storing aggregated peak information."""

    price: float
    timestamps: List[int]
    kind: str

    @property
    def strength(self) -> float:
        """Return normalized strength score based on the number of touches."""
        return min(1.0, len(self.timestamps) / 10)

    @property
    def ts_range(self) -> Tuple[int, int]:
        """Return the minimum and maximum timestamp covered by the level."""
        return min(self.timestamps), max(self.timestamps)


class LevelsService:
    """Service computing price levels from OHLCV data."""

    def detect_levels(self, frame: pd.DataFrame, *, max_levels: int = 10) -> List[LevelCandidate]:
        """Return aggregated support and resistance levels ordered by strength.

        Parameters
        ----------
        frame:
            OHLCV dataframe.
        max_levels:
            Upper bound on the number of levels returned. Keeping the payload
            small avoids overwhelming the SSE and REST consumers.

        """
        if frame.empty:
            return []
        if max_levels <= 0:
            return []
        closes = frame["c"].astype(float).to_numpy(copy=False)
        timestamps = frame["ts"].astype(int).to_list()
        # Determine peak distance heuristically to avoid noise.
        min_distance = max(2, len(frame) // 20)
        price_std = float(np.std(closes)) or 1.0
        prominence = price_std * 0.5

        peaks, _ = find_peaks(closes, distance=min_distance, prominence=prominence)
        troughs, _ = find_peaks(-closes, distance=min_distance, prominence=prominence)

        tolerance = float(np.mean(closes)) * 0.002 or 1.0
        groups: Dict[Tuple[str, int], LevelCandidate] = {}

        def _add(index: int, kind: str) -> None:
            price = float(closes[index])
            bucket = int(price / tolerance) if tolerance else int(price)
            key = (kind, bucket)
            candidate = groups.setdefault(
                key, LevelCandidate(price=price, timestamps=[], kind=kind)
            )
            candidate.price = (candidate.price * len(candidate.timestamps) + price) / (
                len(candidate.timestamps) + 1
            )
            candidate.timestamps.append(timestamps[index])

        for idx in peaks:
            _add(int(idx), "resistance")
        for idx in troughs:
            _add(int(idx), "support")

        sorted_levels = sorted(groups.values(), key=lambda c: c.strength, reverse=True)
        return sorted_levels[:max_levels]


__all__ = ["LevelsService", "LevelCandidate"]
