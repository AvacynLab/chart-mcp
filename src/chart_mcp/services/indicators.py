"""Technical indicator computations using pandas/numpy primitives.

Each helper focuses on a single indicator so the FastAPI routes, the MCP
tools layer and the unit tests can all share the exact same implementation.
We aggressively validate parameters upfront which keeps downstream code free
from repetitive checks and produces consistent error messages.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from chart_mcp.utils.errors import BadRequest


def _validate_window(window: int, *, name: str) -> int:
    """Ensure that the sliding window parameter is strictly positive."""
    if window <= 0:
        raise BadRequest(f"{name} window must be a positive integer")
    return window


def _validate_min_length(frame: pd.DataFrame, window: int) -> None:
    """Ensure the caller provides at least ``window`` rows of OHLCV data."""
    if len(frame) < window:
        raise BadRequest("Not enough data points for indicator computation")


def simple_moving_average(frame: pd.DataFrame, window: int) -> pd.Series:
    """Return simple moving average over the closing price."""
    window = _validate_window(window, name="SMA")
    _validate_min_length(frame, window)
    close_series = frame["c"].astype(float)
    return close_series.rolling(window=window, min_periods=window).mean()


def exponential_moving_average(frame: pd.DataFrame, window: int) -> pd.Series:
    """Return exponential moving average using pandas ewm."""
    window = _validate_window(window, name="EMA")
    _validate_min_length(frame, window)
    close_series = frame["c"].astype(float)
    return close_series.ewm(span=window, adjust=False).mean()


def relative_strength_index(frame: pd.DataFrame, window: int) -> pd.Series:
    """Compute RSI following the classic Wilder smoothing."""
    window = _validate_window(window, name="RSI")
    if window < 2:
        raise BadRequest("RSI window must be >= 2 to compute price deltas")
    _validate_min_length(frame, window)
    close_series = frame["c"].astype(float)
    delta = close_series.diff().to_numpy()
    gain = np.where(delta > 0, delta, 0.0).astype(float)
    loss = np.where(delta < 0, -delta, 0.0).astype(float)
    gain_series = pd.Series(gain, index=frame.index, dtype=float)
    loss_series = pd.Series(loss, index=frame.index, dtype=float)
    avg_gain = gain_series.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss_series.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace({0.0: np.nan})
    rs = rs.replace([np.inf, -np.inf], np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def macd(frame: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute MACD line, signal line and histogram."""
    fast = _validate_window(fast, name="MACD fast")
    slow = _validate_window(slow, name="MACD slow")
    signal = _validate_window(signal, name="MACD signal")
    if slow <= fast:
        raise BadRequest("Slow period must be greater than fast period")
    macd_line = exponential_moving_average(frame, fast) - exponential_moving_average(frame, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger_bands(frame: pd.DataFrame, window: int = 20, stddev: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands around the simple moving average."""
    window = _validate_window(window, name="Bollinger Bands")
    if stddev <= 0:
        raise BadRequest("Standard deviation multiplier must be positive")
    _validate_min_length(frame, window)
    sma = simple_moving_average(frame, window)
    close_series = frame["c"].astype(float)
    std = close_series.rolling(window=window, min_periods=window).std()
    upper = sma + stddev * std
    lower = sma - stddev * std
    return pd.DataFrame({"middle": sma, "upper": upper, "lower": lower})


class IndicatorService:
    """Service responsible for computing indicators on OHLCV data."""

    def compute(self, frame: pd.DataFrame, indicator: str, params: Dict[str, float]) -> pd.DataFrame:
        """Dispatch indicator computation based on the provided name."""
        indicator = indicator.lower()
        if indicator == "ma":
            window = int(params.get("window", 20))
            series = simple_moving_average(frame, window)
            return pd.DataFrame({"ma": series})
        if indicator == "ema":
            window = int(params.get("window", 20))
            series = exponential_moving_average(frame, window)
            return pd.DataFrame({"ema": series})
        if indicator == "rsi":
            window = int(params.get("window", 14))
            series = relative_strength_index(frame, window)
            return pd.DataFrame({"rsi": series})
        if indicator == "macd":
            fast = int(params.get("fast", 12))
            slow = int(params.get("slow", 26))
            signal = int(params.get("signal", 9))
            return macd(frame, fast=fast, slow=slow, signal=signal)
        if indicator == "bbands":
            window = int(params.get("window", 20))
            stddev = float(params.get("stddev", 2.0))
            return bollinger_bands(frame, window=window, stddev=stddev)
        raise BadRequest(f"Unsupported indicator '{indicator}'")


__all__ = [
    "IndicatorService",
    "simple_moving_average",
    "exponential_moving_average",
    "relative_strength_index",
    "macd",
    "bollinger_bands",
]
