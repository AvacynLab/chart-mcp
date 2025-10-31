"""Unit tests for head & shoulders pattern detection heuristics."""

from __future__ import annotations

import pandas as pd

from chart_mcp.services.patterns import PatternsService


def _build_frame(data: dict[str, list[float]]) -> pd.DataFrame:
    """Build a Pandas frame with mandatory OHLCV columns."""
    frame = pd.DataFrame(data)
    # Ensure integer timestamps to mimic exchange payloads.
    frame["ts"] = frame["ts"].astype(int)
    return frame


def test_detects_bearish_head_shoulders_pattern() -> None:
    """A classical head & shoulders should be identified with metadata."""
    service = PatternsService()
    frame = _build_frame(
        {
            "ts": list(range(12)),
            "o": [
                100.0,
                103.5,
                101.2,
                107.5,
                102.1,
                103.8,
                99.5,
                98.4,
                97.2,
                96.1,
                95.4,
                94.8,
            ],
            "h": [
                101.0,
                105.0,
                102.5,
                110.0,
                103.0,
                105.2,
                100.4,
                99.6,
                98.4,
                97.3,
                96.5,
                95.2,
            ],
            "l": [
                99.2,
                100.2,
                99.5,
                101.8,
                99.4,
                100.1,
                97.8,
                96.9,
                96.0,
                95.3,
                94.9,
                94.4,
            ],
            "c": [
                100.5,
                103.2,
                101.0,
                108.7,
                101.9,
                103.1,
                98.9,
                98.0,
                97.0,
                96.0,
                95.2,
                94.6,
            ],
            "v": [1000] * 12,
        }
    )

    patterns = service.detect(frame)
    head_shoulders = next((p for p in patterns if p.name == "head_shoulders"), None)
    assert head_shoulders is not None, "Expected bearish head & shoulders to be detected"
    assert head_shoulders.metadata["direction"] == "bearish"
    assert head_shoulders.metadata["type"] == "head_shoulders"
    indices = head_shoulders.metadata["indices"]
    assert indices == {"iL": 1, "iHead": 3, "iR": 5, "iNeckline1": 2, "iNeckline2": 4}
    assert 0.55 <= head_shoulders.confidence <= 0.9


def test_detects_inverse_head_shoulders_pattern() -> None:
    """The mirror bullish formation should also be detected."""
    service = PatternsService()
    frame = _build_frame(
        {
            "ts": list(range(12)),
            "o": [
                100.0,
                97.5,
                98.8,
                94.2,
                98.0,
                97.1,
                101.3,
                103.0,
                104.2,
                105.6,
                106.8,
                108.0,
            ],
            "h": [
                101.5,
                100.8,
                100.5,
                102.2,
                101.9,
                101.4,
                103.8,
                105.1,
                106.2,
                107.5,
                108.4,
                109.2,
            ],
            "l": [
                98.5,
                95.0,
                96.2,
                91.5,
                96.0,
                95.2,
                99.5,
                100.2,
                101.4,
                102.6,
                103.7,
                104.5,
            ],
            "c": [
                99.8,
                96.1,
                97.4,
                92.8,
                97.2,
                96.4,
                100.7,
                102.4,
                103.6,
                104.9,
                106.1,
                107.4,
            ],
            "v": [950] * 12,
        }
    )

    patterns = service.detect(frame)
    inverse = next((p for p in patterns if p.name == "inverse_head_shoulders"), None)
    assert inverse is not None, "Expected inverse head & shoulders detection"
    assert inverse.metadata["direction"] == "bullish"
    assert inverse.metadata["type"] == "head_shoulders"
    indices = inverse.metadata["indices"]
    assert indices == {"iL": 1, "iHead": 3, "iR": 5, "iNeckline1": 2, "iNeckline2": 4}
    assert 0.55 <= inverse.confidence <= 0.9


def test_random_trend_does_not_trigger_head_shoulders() -> None:
    """Monotonic trends should not create false positives for the pattern."""
    service = PatternsService()
    frame = _build_frame(
        {
            "ts": list(range(12)),
            "o": [100 + i * 0.5 for i in range(12)],
            "h": [100.8 + i * 0.5 for i in range(12)],
            "l": [99.5 + i * 0.5 for i in range(12)],
            "c": [100.2 + i * 0.5 for i in range(12)],
            "v": [800 + i * 5 for i in range(12)],
        }
    )

    patterns = service.detect(frame)
    assert not any(
        p.metadata.get("type") == "head_shoulders" for p in patterns
    ), "Trending series should not yield head & shoulders detections"
