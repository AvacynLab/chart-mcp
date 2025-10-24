"""Tests ensuring database migrations remain idempotent."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from chart_mcp.db.migrations import run_migrations


def test_run_migrations_is_idempotent(tmp_path: Path) -> None:
    """Running migrations twice should not raise and should retain schema elements."""

    db_path = tmp_path / "chart.sqlite3"
    run_migrations(db_path)
    run_migrations(db_path)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        # Verify that the expected tables exist with their unique indexes.
        cursor.execute("PRAGMA table_info(assets)")
        columns = {row[1] for row in cursor.fetchall()}
        assert {"symbol", "exchange", "name"}.issubset(columns)

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("idx_backtest_runs_asset_timeframe_period_start",),
        )
        assert cursor.fetchone(), "Expected index on backtest_runs timeframe uniqueness"
