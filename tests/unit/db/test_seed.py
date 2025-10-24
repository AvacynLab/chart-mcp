"""Tests covering deterministic database seeding."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from chart_mcp.db import SeedData, run_seed


def test_seed_inserts_expected_assets(tmp_path: Path) -> None:
    """The default seed should populate the canonical asset universe exactly once."""
    db_path = tmp_path / "seed.sqlite3"
    run_seed(db_path)
    run_seed(db_path)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT symbol, exchange, name FROM assets ORDER BY symbol")
        rows = cursor.fetchall()
        assert rows == [
            ("AAPL", "NASDAQ", "Apple Inc."),
            ("BTCUSD", "CRYPTO", "Bitcoin / USD"),
            ("EURUSD", "FOREX", "Euro / US Dollar"),
            ("NVDA", "NASDAQ", "NVIDIA Corporation"),
        ]

        cursor.execute(
            "SELECT timeframe, total_return FROM backtest_runs WHERE id=1",
        )
        timeframe, total_return = cursor.fetchone()
        assert timeframe == "1d"
        assert total_return == 0.42


def test_seed_accepts_custom_assets(tmp_path: Path) -> None:
    """Custom assets passed to :func:`run_seed` should be inserted alongside defaults."""
    db_path = tmp_path / "custom.sqlite3"
    extra_assets = [SeedData(symbol="ETHUSD", exchange="CRYPTO", name="Ethereum / USD")]
    run_seed(db_path, assets=extra_assets)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT symbol FROM assets WHERE symbol IN (?, ?) ORDER BY symbol",
            ("BTCUSD", "ETHUSD"),
        )
        assert [row[0] for row in cursor.fetchall()] == ["BTCUSD", "ETHUSD"]
