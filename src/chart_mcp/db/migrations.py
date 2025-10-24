"""Idempotent migrations for the SQLite development database."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from chart_mcp.db.engine import get_database_path

# Statements are kept deliberately small and idempotent. ``IF NOT EXISTS`` guards
# avoid failures on repeated executions which is essential for CI pipelines that
# may rerun migrations across cached workspaces.
_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        exchange TEXT NOT NULL,
        name TEXT,
        UNIQUE(symbol, exchange)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategy_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        version TEXT NOT NULL,
        parameters_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_strategy_versions_unique
        ON strategy_versions(strategy_id, version);
    """,
    """
    CREATE TABLE IF NOT EXISTS backtest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_version_id INTEGER NOT NULL,
        asset_id INTEGER NOT NULL,
        timeframe TEXT NOT NULL,
        period_start INTEGER NOT NULL,
        period_end INTEGER NOT NULL,
        total_return REAL NOT NULL,
        cagr REAL NOT NULL,
        max_drawdown REAL NOT NULL,
        win_rate REAL NOT NULL,
        sharpe REAL NOT NULL,
        profit_factor REAL NOT NULL,
        fees REAL DEFAULT 0,
        slippage REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(strategy_version_id) REFERENCES strategy_versions(id) ON DELETE CASCADE,
        FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_backtest_runs_asset_timeframe_period_start
        ON backtest_runs(asset_id, timeframe, period_start);
    """,
)


def _ensure_parent_directory(path: Path) -> None:
    """Create the parent directory for the SQLite database if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)


def run_migrations(database_path: Path | None = None) -> Path:
    """Apply idempotent schema migrations and return the database path.

    Parameters
    ----------
    database_path:
        Optional override when tests want to operate on a temporary database. By
        default the path is resolved from :func:`chart_mcp.db.engine.get_database_path`.

    """
    path = database_path or get_database_path()
    _ensure_parent_directory(path)
    with closing(sqlite3.connect(path)) as connection:
        cursor = connection.cursor()
        for statement in _SCHEMA_STATEMENTS:
            cursor.executescript(statement)
        connection.commit()
    return path


if __name__ == "__main__":
    target = run_migrations()
    print(f"Migrations applied to {target}")
