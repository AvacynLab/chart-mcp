"""Seed helpers inserting deterministic finance fixtures."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from chart_mcp.db.migrations import run_migrations


@dataclass(frozen=True)
class SeedData:
    """Structured representation of an asset used for deterministic seeds."""

    symbol: str
    exchange: str
    name: str


_DEFAULT_ASSETS: tuple[SeedData, ...] = (
    SeedData(symbol="AAPL", exchange="NASDAQ", name="Apple Inc."),
    SeedData(symbol="NVDA", exchange="NASDAQ", name="NVIDIA Corporation"),
    SeedData(symbol="BTCUSD", exchange="CRYPTO", name="Bitcoin / USD"),
    SeedData(symbol="EURUSD", exchange="FOREX", name="Euro / US Dollar"),
)


def _seed_assets(connection: sqlite3.Connection, assets: Iterable[SeedData]) -> None:
    """Insert assets using ``INSERT OR IGNORE`` to remain idempotent."""

    cursor = connection.cursor()
    for asset in assets:
        cursor.execute(
            """
            INSERT OR IGNORE INTO assets(symbol, exchange, name)
            VALUES (?, ?, ?)
            """,
            (asset.symbol, asset.exchange, asset.name),
        )


def _seed_backtest_strategy(connection: sqlite3.Connection) -> None:
    """Create a canonical SMA crossover strategy for integration tests."""

    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO strategies(id, name, description)
        VALUES (1, 'SMA Crossover', 'Fast/slow moving average crossover baseline')
        """,
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO strategy_versions(id, strategy_id, version, parameters_json)
        VALUES (1, 1, '1.0.0', '{"fast": 50, "slow": 200}')
        """,
    )


def _seed_backtest_runs(connection: sqlite3.Connection) -> None:
    """Populate a deterministic backtest run aligned with fixtures used in tests."""

    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM assets WHERE symbol=? AND exchange=?",
        ("BTCUSD", "CRYPTO"),
    )
    asset_id_row = cursor.fetchone()
    if not asset_id_row:
        raise RuntimeError("BTCUSD asset must exist before seeding backtest runs")
    asset_id = asset_id_row[0]
    cursor.execute(
        """
        INSERT OR IGNORE INTO backtest_runs(
            id,
            strategy_version_id,
            asset_id,
            timeframe,
            period_start,
            period_end,
            total_return,
            cagr,
            max_drawdown,
            win_rate,
            sharpe,
            profit_factor,
            fees,
            slippage,
            created_at
        )
        VALUES (
            1, 1, ?, '1d', 1704067200, 1706745600,
            0.42, 0.65, -0.12, 0.55, 1.8, 1.4, 0.001, 0.0005,
            ?
        )
        """,
        (asset_id, datetime(2024, 2, 1, tzinfo=timezone.utc).isoformat()),
    )


def run_seed(database_path: Path | None = None, *, assets: Iterable[SeedData] | None = None) -> Path:
    """Populate the database with deterministic data and return the path."""

    path = run_migrations(database_path)
    with closing(sqlite3.connect(path)) as connection:
        asset_payload = list(_DEFAULT_ASSETS)
        if assets:
            asset_payload.extend(assets)
        _seed_assets(connection, asset_payload)
        _seed_backtest_strategy(connection)
        _seed_backtest_runs(connection)
        connection.commit()
    return path


if __name__ == "__main__":
    target = run_seed()
    print(f"Seed data inserted into {target}")
