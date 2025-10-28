"""Technical indicator computations using pandas/numpy primitives.

The module exposes well documented helpers for each indicator along with a
thin :class:`IndicatorService` dispatcher that is reused by the REST API, the
SSE streaming pipeline and the MCP tools layer. Centralising the logic keeps
the mathematical formulas, error handling and column naming consistent across
the different entry points.
"""

from __future__ import annotations

from typing import Dict, Mapping

import numpy as np
import pandas as pd

from chart_mcp.utils.errors import BadRequest

#: Canonical indicator identifiers surfaced through the public API.
CANONICAL_INDICATORS: frozenset[str] = frozenset({"ma", "ema", "rsi", "macd", "bbands"})
#: Friendly aliases accepted by the API (currently only ``sma``).
INDICATOR_ALIASES: Mapping[str, str] = {"sma": "ma"}
#: Complete set of accepted identifiers (canonical names + aliases).
SUPPORTED_INDICATORS: frozenset[str] = frozenset(
    set(CANONICAL_INDICATORS) | set(INDICATOR_ALIASES.keys())
)

# Default parameters closely follow technical analysis conventions. Surfacing
# them as constants makes the behaviour explicit and simplifies unit tests.
DEFAULT_SMA_WINDOW = 20
DEFAULT_EMA_WINDOW = 20
DEFAULT_RSI_WINDOW = 14
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_BBANDS_WINDOW = 20
DEFAULT_BBANDS_STDDEV = 2.0


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
    """Return the Simple Moving Average over the closing price column.

    Parameters
    ----------
    frame:
        OHLCV dataframe containing a ``c`` close column.
    window:
        Number of periods over which the arithmetic mean is computed.

    """
    window = _validate_window(window, name="SMA")
    _validate_min_length(frame, window)
    close_series = frame["c"].astype(float)
    series = close_series.rolling(window=window, min_periods=window).mean()
    return series.rename(f"sma_{window}")


def exponential_moving_average(frame: pd.DataFrame, window: int) -> pd.Series:
    """Return the Exponential Moving Average of the closing price.

    The multiplier ``alpha`` used by :meth:`pandas.Series.ewm` is derived from
    the provided window which mirrors the convention used by trading platforms.
    """
    window = _validate_window(window, name="EMA")
    _validate_min_length(frame, window)
    close_series = frame["c"].astype(float)
    series = close_series.ewm(span=window, adjust=False).mean()
    return series.rename(f"ema_{window}")


def relative_strength_index(frame: pd.DataFrame, window: int) -> pd.Series:
    """Compute the Relative Strength Index using Wilder's smoothing method."""
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
    # The first ``window`` samples do not have enough history to compute RSI.
    # Returning 50 keeps the early part of the series neutral, which is the
    # behaviour expected by the front-end overlays and the unit tests.
    return rsi.fillna(50.0).rename(f"rsi_{window}")


def macd(frame: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute Moving Average Convergence Divergence (MACD).

    The implementation follows the classic parameters ``12``/``26``/``9`` but
    allows the caller to override them. The resulting dataframe exposes three
    columns with explicit names so downstream consumers can rely on stable keys:

    ``macd``
        Difference between the fast and slow EMAs.
    ``macd_signal``
        EMA of the MACD line using the ``signal`` period.
    ``macd_hist``
        Histogram showing the divergence between ``macd`` and ``macd_signal``.
    """
    fast = _validate_window(fast, name="MACD fast")
    slow = _validate_window(slow, name="MACD slow")
    signal = _validate_window(signal, name="MACD signal")
    if slow <= fast:
        raise BadRequest("Slow period must be greater than fast period")
    macd_line = exponential_moving_average(frame, fast) - exponential_moving_average(frame, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    result = pd.DataFrame({"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist})
    warmup = max(slow - 1, signal - 1)
    if warmup > 0:
        result.iloc[:warmup] = np.nan
    return result


def bollinger_bands(frame: pd.DataFrame, window: int = 20, stddev: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands around the simple moving average.

    The helper returns a dataframe with the following keys to keep naming
    consistent across the API, SSE stream and documentation:

    ``bb_middle``
        The SMA used as the middle band.
    ``bb_upper``
        Upper band obtained by adding ``stddev`` standard deviations.
    ``bb_lower``
        Lower band obtained by subtracting ``stddev`` standard deviations.
    """
    window = _validate_window(window, name="Bollinger Bands")
    if stddev <= 0:
        raise BadRequest("Standard deviation multiplier must be positive")
    _validate_min_length(frame, window)
    sma = simple_moving_average(frame, window)
    close_series = frame["c"].astype(float)
    std = close_series.rolling(window=window, min_periods=window).std()
    upper = sma + stddev * std
    lower = sma - stddev * std
    return pd.DataFrame({"bb_middle": sma, "bb_upper": upper, "bb_lower": lower})


class IndicatorService:
    """Service responsible for computing indicators on OHLCV data."""

    def compute(
        self, frame: pd.DataFrame, indicator: str, params: Dict[str, float]
    ) -> pd.DataFrame:
        """Dispatch indicator computation based on the provided name."""
        normalized = indicator.lower().strip()
        canonical = INDICATOR_ALIASES.get(normalized, normalized)
        if canonical not in CANONICAL_INDICATORS:
            raise BadRequest(f"Unsupported indicator '{indicator}'")

        if canonical == "ma":
            window = int(params.get("window", DEFAULT_SMA_WINDOW))
            series = simple_moving_average(frame, window)
            column = f"sma_{window}"
            return pd.DataFrame({column: series})
        if canonical == "ema":
            window = int(params.get("window", DEFAULT_EMA_WINDOW))
            series = exponential_moving_average(frame, window)
            column = f"ema_{window}"
            return pd.DataFrame({column: series})
        if canonical == "rsi":
            window = int(params.get("window", DEFAULT_RSI_WINDOW))
            series = relative_strength_index(frame, window)
            column = f"rsi_{window}"
            return pd.DataFrame({column: series})
        if canonical == "macd":
            fast = int(params.get("fast", DEFAULT_MACD_FAST))
            slow = int(params.get("slow", DEFAULT_MACD_SLOW))
            signal = int(params.get("signal", DEFAULT_MACD_SIGNAL))
            return macd(frame, fast=fast, slow=slow, signal=signal)
        if canonical == "bbands":
            window = int(params.get("window", DEFAULT_BBANDS_WINDOW))
            stddev = float(params.get("stddev", DEFAULT_BBANDS_STDDEV))
            return bollinger_bands(frame, window=window, stddev=stddev)
        # The guard above should prevent reaching this branch; keeping the
        # exception for defensive programming in case of future refactors.
        raise BadRequest(f"Unsupported indicator '{indicator}'")


__all__ = [
    "IndicatorService",
    "CANONICAL_INDICATORS",
    "INDICATOR_ALIASES",
    "SUPPORTED_INDICATORS",
    "simple_moving_average",
    "exponential_moving_average",
    "relative_strength_index",
    "macd",
    "bollinger_bands",
]
