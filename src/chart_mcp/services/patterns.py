"""Detection of simple chart patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

import numpy as np
import pandas as pd


@dataclass
class PatternResult:
    """Result of a detected pattern."""

    name: str
    score: float
    start_ts: int
    end_ts: int
    points: List[tuple[int, float]]
    confidence: float


class PatternsService:
    """Service identifying double tops/bottoms, triangles and channels."""

    def detect(self, frame: pd.DataFrame) -> List[PatternResult]:
        """Detect chart patterns on the provided OHLCV frame."""
        if len(frame) < 5:
            return []
        closes = frame["c"].to_numpy()
        highs = frame.get("h", frame["c"]).to_numpy()
        lows = frame.get("l", frame["c"]).to_numpy()
        timestamps = frame["ts"].astype(int).to_numpy()
        results: List[PatternResult] = []
        if len(frame) >= 10:
            results.extend(self._detect_double_extrema(closes, timestamps))
            results.extend(self._detect_triangle(highs, lows, timestamps))
        results.extend(self._detect_channel(closes, timestamps))
        results.extend(self._detect_candlestick_patterns(frame))
        return sorted(results, key=lambda r: r.score, reverse=True)[:5]

    def _local_extrema(
        self, series: np.ndarray, compare: Callable[[float, float, float], bool]
    ) -> List[int]:
        indices: List[int] = []
        for i in range(1, len(series) - 1):
            if compare(series[i - 1], series[i], series[i + 1]):
                indices.append(i)
        return indices

    def _detect_double_extrema(self, closes: np.ndarray, timestamps: np.ndarray) -> List[PatternResult]:
        results: List[PatternResult] = []
        peaks = self._local_extrema(closes, lambda left, center, right: center >= left and center >= right)
        troughs = self._local_extrema(
            closes, lambda left, center, right: center <= left and center <= right
        )
        # Double top
        if len(peaks) >= 2:
            best = sorted(peaks, key=lambda idx: closes[idx], reverse=True)[:2]
            best.sort()
            diff = abs(closes[best[0]] - closes[best[1]]) / max(closes[best[0]], closes[best[1]])
            valley = closes[best[0] : best[1] + 1].min()
            if diff <= 0.015 and valley < min(closes[best[0]], closes[best[1]]) * 0.98:
                results.append(
                    PatternResult(
                        name="double_top",
                        score=0.75,
                        start_ts=int(timestamps[best[0]]),
                        end_ts=int(timestamps[best[1]]),
                        points=[(int(timestamps[idx]), float(closes[idx])) for idx in best],
                        confidence=0.7,
                    )
                )
        # Double bottom
        if len(troughs) >= 2:
            best = sorted(troughs, key=lambda idx: closes[idx])[:2]
            best.sort()
            diff = abs(closes[best[0]] - closes[best[1]]) / max(closes[best[0]], closes[best[1]])
            peak = closes[best[0] : best[1] + 1].max()
            if diff <= 0.015 and peak > max(closes[best[0]], closes[best[1]]) * 1.02:
                results.append(
                    PatternResult(
                        name="double_bottom",
                        score=0.75,
                        start_ts=int(timestamps[best[0]]),
                        end_ts=int(timestamps[best[1]]),
                        points=[(int(timestamps[idx]), float(closes[idx])) for idx in best],
                        confidence=0.7,
                    )
                )
        return results

    def _detect_triangle(
        self, highs: np.ndarray, lows: np.ndarray, timestamps: np.ndarray
    ) -> List[PatternResult]:
        results: List[PatternResult] = []
        window = max(6, len(highs) // 2)
        recent_highs = highs[-window:]
        recent_lows = lows[-window:]
        if len(recent_highs) < 6 or len(recent_lows) < 6:
            return results
        high_slope = np.polyfit(np.arange(len(recent_highs)), recent_highs, 1)[0]
        low_slope = np.polyfit(np.arange(len(recent_lows)), recent_lows, 1)[0]
        if high_slope < 0 and low_slope > 0:
            start_ts = int(timestamps[-window])
            end_ts = int(timestamps[-1])
            spread_start = recent_highs[0] - recent_lows[0]
            spread_end = recent_highs[-1] - recent_lows[-1]
            if spread_end < spread_start:
                score = min(0.85, (spread_start - spread_end) / max(spread_start, 1e-6))
                points = [
                    (start_ts, float(recent_highs[0])),
                    (end_ts, float(recent_highs[-1])),
                    (start_ts, float(recent_lows[0])),
                    (end_ts, float(recent_lows[-1])),
                ]
                results.append(
                    PatternResult(
                        name="triangle",
                        score=float(max(score, 0.4)),
                        start_ts=start_ts,
                        end_ts=end_ts,
                        points=points,
                        confidence=0.6,
                    )
                )
        return results

    def _detect_channel(self, closes: np.ndarray, timestamps: np.ndarray) -> List[PatternResult]:
        results: List[PatternResult] = []
        x = np.arange(len(closes))
        slope, intercept = np.polyfit(x, closes, 1)
        trend = slope * x + intercept
        residuals = closes - trend
        width = float(np.ptp(residuals))
        if width <= max(1e-6, np.mean(closes) * 0.02):
            points = [
                (int(timestamps[0]), float(trend[0])),
                (int(timestamps[-1]), float(trend[-1])),
            ]
            score = max(0.4, 1.0 - width / (np.mean(closes) * 0.02))
            results.append(
                PatternResult(
                    name="channel",
                    score=float(min(score, 0.85)),
                    start_ts=int(timestamps[0]),
                    end_ts=int(timestamps[-1]),
                    points=points,
                    confidence=0.5,
                )
            )
        return results

    def _detect_candlestick_patterns(self, frame: pd.DataFrame) -> List[PatternResult]:
        """Detect hammer and engulfing candlestick setups.

        The heuristics implemented here favour precision over recall so that
        noisy inputs do not generate spurious alerts.  Only the most recent
        candles (last twenty) are analysed to keep the computation bounded.
        """

        opens = frame["o"].to_numpy()
        closes = frame["c"].to_numpy()
        highs = frame.get("h", frame["c"]).to_numpy()
        lows = frame.get("l", frame["c"]).to_numpy()
        timestamps = frame["ts"].astype(int).to_numpy()

        if len(opens) < 2:
            return []

        results: List[PatternResult] = []
        window_start = max(1, len(opens) - 20)

        for idx in range(window_start, len(opens)):
            prev_idx = idx - 1
            if np.isnan(opens[idx]) or np.isnan(closes[idx]):
                continue

            body = abs(closes[idx] - opens[idx])
            total_range = max(highs[idx] - lows[idx], 1e-9)
            lower_shadow = min(opens[idx], closes[idx]) - lows[idx]
            upper_shadow = highs[idx] - max(opens[idx], closes[idx])

            if body < 1e-6:
                # Skip doji-like candles that would inflate ratios.
                continue

            if self._is_downtrend(closes, idx):
                # Bullish hammer detection.
                hammer_ratio = lower_shadow / body
                close_to_high = (highs[idx] - closes[idx]) / total_range
                if hammer_ratio >= 2.0 and close_to_high <= 0.2:
                    results.append(
                        PatternResult(
                            name="bullish_hammer",
                            score=0.65,
                            start_ts=int(timestamps[idx]),
                            end_ts=int(timestamps[idx]),
                            points=[
                                (int(timestamps[idx]), float(lows[idx])),
                                (int(timestamps[idx]), float(highs[idx])),
                            ],
                            confidence=0.55,
                        )
                    )

            if self._is_uptrend(closes, idx):
                # Bearish hammer (hanging man) check using mirrored conditions.
                hammer_ratio = upper_shadow / body
                close_to_low = (closes[idx] - lows[idx]) / total_range
                if hammer_ratio >= 2.0 and close_to_low <= 0.2:
                    results.append(
                        PatternResult(
                            name="bearish_hammer",
                            score=0.65,
                            start_ts=int(timestamps[idx]),
                            end_ts=int(timestamps[idx]),
                            points=[
                                (int(timestamps[idx]), float(lows[idx])),
                                (int(timestamps[idx]), float(highs[idx])),
                            ],
                            confidence=0.55,
                        )
                    )

            # Engulfing patterns require at least one candle of history.
            prev_body = abs(closes[prev_idx] - opens[prev_idx])
            if prev_body < 1e-6:
                continue

            if (
                closes[prev_idx] < opens[prev_idx]
                and closes[idx] > opens[idx]
                and opens[idx] <= closes[prev_idx]
                and closes[idx] >= opens[prev_idx]
                and body >= 1.1 * prev_body
            ):
                # Bullish engulfing pattern following a downtrend.
                if self._is_downtrend(closes, idx):
                    results.append(
                        PatternResult(
                            name="bullish_engulfing",
                            score=0.7,
                            start_ts=int(timestamps[prev_idx]),
                            end_ts=int(timestamps[idx]),
                            points=[
                                (int(timestamps[prev_idx]), float(opens[prev_idx])),
                                (int(timestamps[idx]), float(closes[idx])),
                            ],
                            confidence=0.6,
                        )
                    )

            if (
                closes[prev_idx] > opens[prev_idx]
                and closes[idx] < opens[idx]
                and opens[idx] >= closes[prev_idx]
                and closes[idx] <= opens[prev_idx]
                and body >= 1.1 * prev_body
            ):
                # Bearish engulfing pattern following an uptrend.
                if self._is_uptrend(closes, idx):
                    results.append(
                        PatternResult(
                            name="bearish_engulfing",
                            score=0.7,
                            start_ts=int(timestamps[prev_idx]),
                            end_ts=int(timestamps[idx]),
                            points=[
                                (int(timestamps[prev_idx]), float(opens[prev_idx])),
                                (int(timestamps[idx]), float(closes[idx])),
                            ],
                            confidence=0.6,
                        )
                    )

        return results

    def _is_downtrend(self, closes: np.ndarray, idx: int, lookback: int = 4) -> bool:
        """Return ``True`` when the recent closes slope downward."""

        end = idx
        start = max(0, end - lookback - 1)
        window = closes[start:end]
        if len(window) < 3:
            return False
        slope = np.polyfit(np.arange(len(window)), window, 1)[0]
        return bool(slope < 0)

    def _is_uptrend(self, closes: np.ndarray, idx: int, lookback: int = 4) -> bool:
        """Return ``True`` when the recent closes slope upward."""

        end = idx
        start = max(0, end - lookback - 1)
        window = closes[start:end]
        if len(window) < 3:
            return False
        slope = np.polyfit(np.arange(len(window)), window, 1)[0]
        return bool(slope > 0)


__all__ = ["PatternsService", "PatternResult"]
