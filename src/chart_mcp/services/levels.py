"""Detection of support and resistance levels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


@dataclass
class LevelCandidate:
    """Intermediate structure storing aggregated peak information."""

    price: float
    timestamps: List[int]
    kind: str

    @property
    def strength(self) -> float:
        return min(1.0, len(self.timestamps) / 10)

    @property
    def ts_range(self) -> Tuple[int, int]:
        return min(self.timestamps), max(self.timestamps)


class LevelsService:
    """Service computing price levels from OHLCV data."""

    def detect_levels(self, frame: pd.DataFrame) -> List[LevelCandidate]:
        """Return aggregated support and resistance levels."""

        if frame.empty:
            return []
        closes = frame["c"].to_numpy()
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
            candidate = groups.setdefault(key, LevelCandidate(price=price, timestamps=[], kind=kind))
            candidate.price = (candidate.price * len(candidate.timestamps) + price) / (
                len(candidate.timestamps) + 1
            )
            candidate.timestamps.append(timestamps[index])

        for idx in peaks:
            _add(int(idx), "resistance")
        for idx in troughs:
            _add(int(idx), "support")

        return sorted(groups.values(), key=lambda c: c.strength, reverse=True)


__all__ = ["LevelsService", "LevelCandidate"]
