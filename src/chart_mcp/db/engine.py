"""Helpers for resolving the database location used by migrations and seeds."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_SQLITE_PATH = Path("data") / "chart_mcp.sqlite3"


def get_database_path() -> Path:
    """Return the resolved database file path.

    The backend primarily targets PostgreSQL, but in CI and local development we
    leverage SQLite to keep migrations idempotent and lightweight. When the
    ``POSTGRES_URL`` environment variable is provided with a ``sqlite:///`` URI
    we honour the path. Otherwise we fall back to ``data/chart_mcp.sqlite3``.
    """

    raw_url = os.environ.get("POSTGRES_URL")
    if raw_url and raw_url.startswith("sqlite://"):
        _, _, sqlite_path = raw_url.partition("sqlite:///")
        if sqlite_path:
            return Path(sqlite_path).expanduser().resolve()
    return (_DEFAULT_SQLITE_PATH).expanduser().resolve()
