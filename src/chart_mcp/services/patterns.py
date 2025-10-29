"""Pattern detection heuristics shared between the API and SSE layers.

The service favours deterministic heuristics with explicit thresholds rather
than machine-learning black boxes so the front-end can confidently render the
results to users.  Each helper documents the maths used to rank the detected
structures and the metadata exposed to downstream consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

import numpy as np
import pandas as pd


@dataclass
class PatternResult:
    """Result of a detected pattern.

    Attributes
    ----------
    name:
        Identifier describing the pattern family (``head_shoulders`` for
        instance).
    score:
        Relative quality score normalised in ``[0, 1]`` so the UI can order the
        candidates.
    start_ts / end_ts:
        Timestamp range covering the detected structure.  The interval is used
        to draw overlays on charts.
    points:
        Sequence of anchor points (timestamp, price) illustrating the
        underlying geometry.  They give downstream renderers enough context to
        highlight the formation without recomputing the heuristic.
    confidence:
        Confidence ratio derived from the stability checks implemented by each
        detector.  Values closer to ``1`` indicate high quality matches.
    metadata:
        Extra machine-readable hints such as ``direction`` or specific candle
        indices.
    """

    name: str
    score: float
    start_ts: int
    end_ts: int
    points: List[tuple[int, float]]
    confidence: float
    metadata: Dict[str, object] = field(default_factory=dict)


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
            results.extend(self._detect_head_shoulders(highs, lows, timestamps))
        results.extend(self._detect_channel(closes, timestamps))
        results.extend(self._detect_candlestick_patterns(frame))
        return sorted(results, key=lambda r: r.score, reverse=True)[:5]

    def _detect_head_shoulders(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        timestamps: np.ndarray,
    ) -> List[PatternResult]:
        """Detect classical and inverse head & shoulders formations.

        The implementation uses a lightweight heuristic based on three local
        extrema separated by at least one candle, ensuring that the middle
        extremum (the head) stands out from the shoulders while the neckline
        remains reasonably flat.  Additional metadata describing the indices of
        each key point is attached so downstream consumers can render the
        structure on charts.
        """

        def _build_metadata(
            indices: Dict[str, int],
            direction: str,
        ) -> Dict[str, object]:
            return {
                "type": "head_shoulders",
                "direction": direction,
                "indices": indices,
            }

        results: List[PatternResult] = []
        min_spacing = 2  # Require at least one bar between the extremums.

        # Bearish head & shoulders built from local maxima.
        peak_indices = self._local_extrema(
            highs, lambda left, center, right: center >= left and center >= right
        )
        for a in range(len(peak_indices) - 2):
            left_idx, head_idx, right_idx = peak_indices[a : a + 3]
            if head_idx - left_idx < min_spacing or right_idx - head_idx < min_spacing:
                continue
            left_height = float(highs[left_idx])
            head_height = float(highs[head_idx])
            right_height = float(highs[right_idx])
            shoulder_avg = (left_height + right_height) / 2.0
            if shoulder_avg <= 0:
                continue
            # Normalised elevation of the head compared to the average shoulder height.
            head_lift = (head_height - shoulder_avg) / shoulder_avg
            if head_lift < 0.02:  # Head must be at least 2 % above the shoulders.
                continue
            # Shoulder symmetry ensures both sides keep similar amplitude (<5 % gap).
            shoulder_similarity = 1.0 - abs(left_height - right_height) / max(
                left_height, right_height
            )
            if shoulder_similarity < 0.95:
                continue
            neck_left_rel = lows[left_idx + 1 : head_idx]
            neck_right_rel = lows[head_idx + 1 : right_idx]
            if len(neck_left_rel) == 0 or len(neck_right_rel) == 0:
                continue
            neck_left_offset = int(np.argmin(neck_left_rel))
            neck_right_offset = int(np.argmin(neck_right_rel))
            neck_left_idx = left_idx + 1 + neck_left_offset
            neck_right_idx = head_idx + 1 + neck_right_offset
            neck_left = float(lows[neck_left_idx])
            neck_right = float(lows[neck_right_idx])
            neck_avg = (neck_left + neck_right) / 2.0
            if neck_avg == 0:
                continue
            neckline_diff = abs(neck_left - neck_right) / max(neck_avg, 1e-9)
            if neckline_diff > 0.03:
                continue
            # Blend prominence and symmetry into a bounded scoring heuristic.
            score = float(
                min(
                    0.9,
                    0.6 + 0.2 * min(head_lift / 0.1, 1.0) + 0.2 * shoulder_similarity,
                )
            )
            # Confidence leans on symmetry and neckline alignment for stability.
            confidence = float(
                max(0.55, min(0.9, 0.5 * shoulder_similarity + 0.5 * (1.0 - neckline_diff)))
            )
            indices = {
                "iL": int(left_idx),
                "iHead": int(head_idx),
                "iR": int(right_idx),
                "iNeckline1": int(neck_left_idx),
                "iNeckline2": int(neck_right_idx),
            }
            results.append(
                PatternResult(
                    name="head_shoulders",
                    score=score,
                    start_ts=int(timestamps[left_idx]),
                    end_ts=int(timestamps[right_idx]),
                    points=[
                        (int(timestamps[left_idx]), left_height),
                        (int(timestamps[head_idx]), head_height),
                        (int(timestamps[right_idx]), right_height),
                        (int(timestamps[neck_left_idx]), neck_left),
                        (int(timestamps[neck_right_idx]), neck_right),
                    ],
                    confidence=confidence,
                    metadata=_build_metadata(indices, "bearish"),
                )
            )

        # Bullish inverse head & shoulders built from local minima.
        trough_indices = self._local_extrema(
            lows, lambda left, center, right: center <= left and center <= right
        )
        for a in range(len(trough_indices) - 2):
            left_idx, head_idx, right_idx = trough_indices[a : a + 3]
            if head_idx - left_idx < min_spacing or right_idx - head_idx < min_spacing:
                continue
            left_depth = float(lows[left_idx])
            head_depth = float(lows[head_idx])
            right_depth = float(lows[right_idx])
            shoulder_avg = (left_depth + right_depth) / 2.0
            if shoulder_avg == 0:
                continue
            # Normalised depth of the head compared to the shoulders (inverse pattern).
            head_drop = (shoulder_avg - head_depth) / abs(shoulder_avg)
            if head_drop < 0.02:
                continue
            # Symmetry check mirrored on trough depths (<5 % deviation tolerated).
            shoulder_similarity = 1.0 - abs(left_depth - right_depth) / max(
                abs(left_depth), abs(right_depth)
            )
            if shoulder_similarity < 0.95:
                continue
            neck_left_rel = highs[left_idx + 1 : head_idx]
            neck_right_rel = highs[head_idx + 1 : right_idx]
            if len(neck_left_rel) == 0 or len(neck_right_rel) == 0:
                continue
            neck_left_offset = int(np.argmax(neck_left_rel))
            neck_right_offset = int(np.argmax(neck_right_rel))
            neck_left_idx = left_idx + 1 + neck_left_offset
            neck_right_idx = head_idx + 1 + neck_right_offset
            neck_left = float(highs[neck_left_idx])
            neck_right = float(highs[neck_right_idx])
            neck_avg = (neck_left + neck_right) / 2.0
            if neck_avg == 0:
                continue
            neckline_diff = abs(neck_left - neck_right) / max(abs(neck_avg), 1e-9)
            if neckline_diff > 0.03:
                continue
            score = float(
                min(
                    0.9,
                    0.6 + 0.2 * min(head_drop / 0.1, 1.0) + 0.2 * shoulder_similarity,
                )
            )
            confidence = float(
                max(0.55, min(0.9, 0.5 * shoulder_similarity + 0.5 * (1.0 - neckline_diff)))
            )
            indices = {
                "iL": int(left_idx),
                "iHead": int(head_idx),
                "iR": int(right_idx),
                "iNeckline1": int(neck_left_idx),
                "iNeckline2": int(neck_right_idx),
            }
            results.append(
                PatternResult(
                    name="inverse_head_shoulders",
                    score=score,
                    start_ts=int(timestamps[left_idx]),
                    end_ts=int(timestamps[right_idx]),
                    points=[
                        (int(timestamps[left_idx]), left_depth),
                        (int(timestamps[head_idx]), head_depth),
                        (int(timestamps[right_idx]), right_depth),
                        (int(timestamps[neck_left_idx]), neck_left),
                        (int(timestamps[neck_right_idx]), neck_right),
                    ],
                    confidence=confidence,
                    metadata=_build_metadata(indices, "bullish"),
                )
            )

        return results

    def _local_extrema(
        self, series: np.ndarray, compare: Callable[[float, float, float], bool]
    ) -> List[int]:
        indices: List[int] = []
        for i in range(1, len(series) - 1):
            if compare(series[i - 1], series[i], series[i + 1]):
                indices.append(i)
        return indices

    def _detect_double_extrema(
        self, closes: np.ndarray, timestamps: np.ndarray
    ) -> List[PatternResult]:
        results: List[PatternResult] = []
        peaks = self._local_extrema(
            closes, lambda left, center, right: center >= left and center >= right
        )
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
        tolerance = max(1e-6, np.mean(closes) * 0.02)
        if width <= tolerance:
            points = [
                (int(timestamps[0]), float(trend[0])),
                (int(timestamps[-1]), float(trend[-1])),
            ]
            score = max(0.4, 1.0 - width / (np.mean(closes) * 0.02))
            rmse = float(np.sqrt(np.mean(np.square(residuals))))
            # Convert the deviation into a bounded ratio so that a perfect fit keeps
            # the confidence near 0.8 whereas noisy channels fall back toward 0.3.
            ratio = min(1.0, rmse / tolerance)
            confidence = max(0.3, min(0.8, 0.8 - 0.5 * ratio))
            results.append(
                PatternResult(
                    name="channel",
                    score=float(min(score, 0.85)),
                    start_ts=int(timestamps[0]),
                    end_ts=int(timestamps[-1]),
                    points=points,
                    confidence=confidence,
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
                and self._is_downtrend(closes, idx)
            ):
                # Bullish engulfing pattern following a downtrend.
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
                and self._is_uptrend(closes, idx)
            ):
                # Bearish engulfing pattern following an uptrend.
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
