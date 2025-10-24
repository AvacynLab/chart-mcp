"""Tests covering hammer and engulfing candlestick detection heuristics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from chart_mcp.services.patterns import PatternsService


def _frame(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> pd.DataFrame:
    """Return a minimal OHLCV frame using synthetic timestamp and volume data."""
    return pd.DataFrame(
        {
            "ts": list(range(len(opens))),
            "o": opens,
            "h": highs,
            "l": lows,
            "c": closes,
            "v": [100] * len(opens),
        }
    )


def test_noise_frame_does_not_emit_candlestick_patterns() -> None:
    """Random walks should not produce hammer or engulfing signals."""
    rng = np.random.default_rng(42)
    prices = np.cumsum(rng.normal(0.0, 0.3, size=40)) + 100
    opens = prices[:-1].tolist() + [prices[-1]]
    closes = prices.tolist()
    highs = (np.maximum(opens, closes) + 0.1).tolist()
    lows = (np.minimum(opens, closes) - 0.1).tolist()
    frame = _frame(opens, highs, lows, closes)

    service = PatternsService()
    names = {result.name for result in service.detect(frame)}

    assert "bullish_hammer" not in names
    assert "bearish_hammer" not in names
    assert "bullish_engulfing" not in names
    assert "bearish_engulfing" not in names


def test_bullish_hammer_detected_after_downtrend() -> None:
    """A long lower shadow with a preceding sell-off should raise a hammer."""
    opens = [20, 19, 18, 17, 16, 15.2, 14.5, 14.2, 14.0, 13.8]
    closes = [19.5, 18.5, 17.8, 16.5, 15.8, 15.0, 14.2, 14.4, 14.6, 15.2]
    highs = [o + 0.4 for o in opens]
    lows = [c - 0.2 for c in closes]
    # Create the hammer on the last candle: deep lower shadow and close near the high.
    lows[-1] = 11.0
    highs[-1] = 15.4
    frame = _frame(opens, highs, lows, closes)

    service = PatternsService()
    names = {result.name for result in service.detect(frame)}

    assert "bullish_hammer" in names


def test_engulfing_patterns_require_trend_context() -> None:
    """Verify bullish and bearish engulfing recognition with explicit trends."""
    # Downtrend followed by a bullish engulfing candle.
    opens = [50, 49, 48, 47, 46, 45]
    closes = [49, 48, 47, 46, 45, 47]
    highs = [max(o, c) + 0.2 for o, c in zip(opens, closes, strict=False)]
    lows = [min(o, c) - 0.2 for o, c in zip(opens, closes, strict=False)]
    frame = _frame(opens, highs, lows, closes)

    service = PatternsService()
    names = {result.name for result in service.detect(frame)}

    assert "bullish_engulfing" in names

    # Append an uptrend culminating in a bearish engulfing candle.
    opens.extend([47.5, 48.5, 49.5, 50.5])
    closes.extend([48.0, 49.0, 50.0, 48.0])
    highs.extend([max(o, c) + 0.2 for o, c in zip(opens[-4:], closes[-4:], strict=False)])
    lows.extend([min(o, c) - 0.2 for o, c in zip(opens[-4:], closes[-4:], strict=False)])
    frame = _frame(opens, highs, lows, closes)

    names = {result.name for result in service.detect(frame)}

    assert "bearish_engulfing" in names
