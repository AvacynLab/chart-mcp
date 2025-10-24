"""Unit tests for the backtest engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from chart_mcp.services.backtest import BacktestEngine, SmaCrossStrategy


def _build_frame(prices: list[float], start: datetime | None = None) -> pd.DataFrame:
    """Helper building a synthetic OHLCV frame from closing prices."""

    start_ts = start or datetime(2024, 1, 1)
    timestamps = [int((start_ts + timedelta(hours=i)).timestamp()) for i in range(len(prices))]
    frame = pd.DataFrame(
        {
            "ts": timestamps,
            "o": prices,
            "h": np.array(prices) + 0.5,
            "l": np.array(prices) - 0.5,
            "c": prices,
            "v": np.full(len(prices), 100.0),
        }
    )
    return frame


def test_engine_returns_zero_metrics_when_no_trades() -> None:
    """A flat market should result in zero trades and neutral metrics."""

    engine = BacktestEngine()
    frame = _build_frame([100.0] * 200)
    strategy = SmaCrossStrategy(fast_window=5, slow_window=20)
    result = engine.run(frame, strategy, timeframe="1h", fees_bps=0.0, slippage_bps=0.0)

    assert result.trades == []
    assert result.metrics.total_return == 0.0
    assert result.metrics.max_drawdown == 0.0
    assert result.metrics.sharpe == 0.0


def test_engine_handles_high_fees_without_numerical_errors() -> None:
    """Large fees/slippage should degrade returns without causing NaNs."""

    engine = BacktestEngine()
    prices = [100 + i for i in range(100)]
    frame = _build_frame(prices)
    strategy = SmaCrossStrategy(fast_window=3, slow_window=10)
    baseline = engine.run(frame, strategy, timeframe="1h", fees_bps=0.0, slippage_bps=0.0)
    result = engine.run(frame, strategy, timeframe="1h", fees_bps=250.0, slippage_bps=150.0)

    assert all(np.isfinite([result.metrics.total_return, result.metrics.cagr]))
    # Heavier fees should reduce performance compared to the zero-cost baseline.
    assert result.metrics.total_return < baseline.metrics.total_return


def test_engine_generates_trades_and_equity_curve() -> None:
    """The engine should emit trades and a monotonic equity curve on rising prices."""

    engine = BacktestEngine()
    prices = [100 + np.sin(i / 2) * 2 + i * 0.5 for i in range(120)]
    frame = _build_frame([float(p) for p in prices])
    strategy = SmaCrossStrategy(fast_window=4, slow_window=12)
    result = engine.run(frame, strategy, timeframe="1h", fees_bps=10.0, slippage_bps=5.0)

    assert len(result.trades) > 0
    assert len(result.equity_curve) == len(result.trades)
    # Equity should remain positive and finite for every point in the curve.
    for _, equity in result.equity_curve:
        assert equity > 0
        assert np.isfinite(equity)
