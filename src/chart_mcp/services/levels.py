"""Detection of support and resistance levels using statistical heuristics.

The implementation follows three stages:

* locate swing highs and lows with :func:`scipy.signal.find_peaks`
* cluster peaks that are close in price into aggregate support/resistance bands
* score each cluster to distinguish between strong and general levels

The scoring formula intentionally favours levels with multiple touches spread
across the analysed window while penalising unstable (high variance) clusters.
The resulting :class:`LevelCandidate` is consumed by both the REST and SSE
layers so we keep the API minimal and well documented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple

import numpy as np
import pandas as pd
from scipy.signal import find_peaks  # type: ignore[import-untyped]


@dataclass
class LevelCandidate:
    """Aggregated metadata describing a support or resistance level.

    Parameters
    ----------
    kind:
        Either ``"support"`` or ``"resistance"`` to describe the market
        structure being tracked.
    window_start/window_end:
        Timestamp boundaries of the analysed OHLCV window. They are leveraged
        to compute recency and coverage ratios in the strength scoring logic.
    merge_threshold:
        Relative tolerance used when clustering peaks. Retained for the
        strength calculation so we can normalise the price volatility.
    prices/timestamps/indices:
        Mutable collections recording raw peak information. Keeping the raw
        touches enables downstream visualisation layers to reconstruct the
        points that participated in the level.

    """

    kind: Literal["support", "resistance"]
    window_start: int
    window_end: int
    merge_threshold: float
    prices: List[float] = field(default_factory=list)
    timestamps: List[int] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)

    def add_touch(self, price: float, timestamp: int, index: int) -> None:
        """Record a new touch contributing to the aggregated level.

        Notes
        -----
        We keep the raw ``index`` for potential future visual overlays where
        highlighting the exact candles forming the level helps users. The
        resulting metadata is also valuable during testing to check the
        clustering behaviour deterministically.

        """
        self.prices.append(float(price))
        self.timestamps.append(int(timestamp))
        self.indices.append(int(index))

    @property
    def price(self) -> float:
        """Average price of the level computed from all touches."""
        if not self.prices:
            return 0.0
        return float(np.mean(self.prices))

    @property
    def touches(self) -> int:
        """Total number of touches contributing to the level."""
        return len(self.timestamps)

    @property
    def ts_range(self) -> Tuple[int, int]:
        """Return the earliest and latest timestamp for this level."""
        if not self.timestamps:
            return self.window_start, self.window_end
        return min(self.timestamps), max(self.timestamps)

    @property
    def _window_span(self) -> int:
        """Helper returning the analysed window duration (guarded against 0)."""
        return max(self.window_end - self.window_start, 1)

    @property
    def _price_deviation_ratio(self) -> float:
        """Normalised intra-level volatility used in the strength formula."""
        if self.touches <= 1:
            return 0.0
        std = float(np.std(self.prices))
        baseline = max(abs(self.price) * self.merge_threshold, 1e-8)
        return min(std / baseline, 1.0)

    @property
    def _coverage_ratio(self) -> float:
        """Ratio describing how the touches span the analysed timeframe."""
        if self.touches <= 1:
            return 0.0
        start, end = self.ts_range
        span = max(end - start, 0)
        return min(span / self._window_span, 1.0)

    @property
    def _recency_ratio(self) -> float:
        """Recency score favouring levels with recent confirmations."""
        if not self.timestamps:
            return 0.0
        latest = max(self.timestamps)
        distance_from_end = self.window_end - latest
        return max(0.0, 1.0 - (distance_from_end / self._window_span))

    @property
    def strength(self) -> float:
        """Composite strength score in ``[0, 1]``.

        The heuristic blends four components:

        * **touch density** (55%): more touches imply higher confidence
        * **price stability** (20%): a narrow cluster suggests a clean level
        * **temporal coverage** (15%): confirmations spaced over time are better
        * **recency** (10%): very old levels are down-weighted

        """
        if self.touches == 0:
            return 0.0
        touch_score = min(self.touches / 4, 1.0)
        stability_score = 1.0 - self._price_deviation_ratio
        coverage_score = self._coverage_ratio
        recency_score = self._recency_ratio
        weighted = (
            touch_score * 0.55
            + stability_score * 0.20
            + coverage_score * 0.15
            + recency_score * 0.10
        )
        return float(round(min(max(weighted, 0.0), 1.0), 4))

    @property
    def strength_label(self) -> Literal["fort", "général"]:
        """Categorise the level as ``fort`` or ``général`` for the UI."""
        return "fort" if self.strength >= 0.65 else "général"


class LevelsService:
    """Service computing price levels from OHLCV data."""

    def detect_levels(
        self,
        frame: pd.DataFrame,
        *,
        max_levels: int = 10,
        distance: int | None = None,
        prominence: float | None = None,
        merge_threshold: float = 0.0025,
        min_touches: int = 2,
    ) -> List[LevelCandidate]:
        """Return aggregated support and resistance levels ordered by strength.

        Parameters
        ----------
        frame:
            OHLCV dataframe sorted by timestamp. The method creates a copy to
            avoid mutating the caller data when enforcing ordering guarantees.
        max_levels:
            Upper bound on the number of levels returned. Keeping the payload
            small avoids overwhelming the SSE and REST consumers.
        distance:
            Optional override for the peak distance passed to
            :func:`scipy.signal.find_peaks`. Defaults to a heuristic based on
            the window length.
        prominence:
            Optional override for the prominence passed to ``find_peaks``. When
            omitted the service derives a value from the observed volatility.
        merge_threshold:
            Relative price tolerance (percentage) used when clustering nearby
            peaks into a single level.
        min_touches:
            Minimum number of touches a cluster must accumulate to be returned.
            If no cluster matches, the constraint is relaxed to keep at least
            one level in the response.

        """
        if frame.empty or max_levels <= 0:
            return []
        sanitized = frame.sort_values("ts", kind="stable").reset_index(drop=True)
        closes = sanitized["c"].astype(float).to_numpy(copy=False)
        timestamps = sanitized["ts"].astype(int).to_numpy(copy=False)
        window_start = int(timestamps[0])
        window_end = int(timestamps[-1])

        if merge_threshold <= 0:
            raise ValueError("merge_threshold must be positive")

        peak_distance = (
            max(1, int(distance)) if distance is not None else max(2, len(sanitized) // 25)
        )
        volatility = float(np.std(closes))
        price_range = float(np.max(closes) - np.min(closes))
        default_prominence = max(volatility * 0.5, price_range * 0.015, 1e-8)
        peak_prominence = float(prominence) if prominence is not None else default_prominence
        peak_prominence = max(peak_prominence, 1e-8)

        peaks, _ = find_peaks(closes, distance=peak_distance, prominence=peak_prominence)
        troughs, _ = find_peaks(-closes, distance=peak_distance, prominence=peak_prominence)

        clusters: Dict[str, List[LevelCandidate]] = {"support": [], "resistance": []}

        def _assign(index: int, kind: Literal["support", "resistance"]) -> None:
            price = float(closes[index])
            ts = int(timestamps[index])
            bucket = clusters[kind]
            for candidate in bucket:
                tolerance = max(candidate.price, price) * merge_threshold
                tolerance = max(tolerance, merge_threshold)
                if abs(candidate.price - price) <= tolerance:
                    candidate.add_touch(price, ts, index)
                    return
            candidate = LevelCandidate(
                kind=kind,
                window_start=window_start,
                window_end=window_end,
                merge_threshold=merge_threshold,
            )
            candidate.add_touch(price, ts, index)
            bucket.append(candidate)

        for idx in peaks:
            _assign(int(idx), "resistance")
        for idx in troughs:
            _assign(int(idx), "support")

        raw_candidates = clusters["support"] + clusters["resistance"]
        if not raw_candidates:
            return []
        min_touches = max(1, int(min_touches))
        filtered = [candidate for candidate in raw_candidates if candidate.touches >= min_touches]
        if not filtered and min_touches > 1:
            filtered = [candidate for candidate in raw_candidates if candidate.touches >= 1]

        ranked = sorted(filtered, key=lambda c: (c.strength, c.touches), reverse=True)
        return ranked[:max_levels]


__all__ = ["LevelsService", "LevelCandidate"]
