"""Tests ensuring database migrations remain idempotent."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
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


def test_module_entrypoint_executes_via_python_m(tmp_path: Path) -> None:
    """Calling ``python -m chart_mcp.db.migrations`` should succeed without PYTHONPATH hacks."""
    env = os.environ.copy()
    database_path = tmp_path / "cli.sqlite3"
    env["POSTGRES_URL"] = f"sqlite:///{database_path}"

    repo_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        [sys.executable, "-m", "chart_mcp.db.migrations"],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
    )

    assert database_path.exists(), "CLI invocation should create the SQLite database"
    assert "Migrations applied" in result.stdout
