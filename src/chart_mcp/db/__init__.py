"""Database utilities for :mod:`chart_mcp` with lightweight import wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .engine import get_database_path

if TYPE_CHECKING:  # pragma: no cover - import-time hints only
    from pathlib import Path

__all__ = ["get_database_path", "run_migrations", "run_seed", "SeedData"]


def run_migrations(database_path: "Path | None" = None) -> "Path":
    """Import and execute :func:`chart_mcp.db.migrations.run_migrations` lazily."""
    from .migrations import run_migrations as _run_migrations

    return _run_migrations(database_path)


def run_seed(database_path: "Path | None" = None, *, assets=None) -> "Path":
    """Import and execute :func:`chart_mcp.db.seed.run_seed` lazily."""
    from .seed import run_seed as _run_seed

    return _run_seed(database_path, assets=assets)


def __getattr__(name: str):  # pragma: no cover - thin lazy import shim
    """Expose lazily imported attributes such as :class:`SeedData`."""
    if name == "SeedData":
        from .seed import SeedData as _SeedData

        return _SeedData
    raise AttributeError(name)
