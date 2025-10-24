"""Test harness hook ensuring ``src`` is importable without editable installs.

This module is imported automatically by Python's :mod:`site` machinery whenever it
detects a ``sitecustomize`` module on ``sys.path``.  By inserting the repository's
``src`` directory near the front of ``sys.path`` we make the ``chart_mcp`` package
importable for ad-hoc commands such as ``python -m chart_mcp.db.migrations`` without
requiring contributors to manipulate ``PYTHONPATH`` or install the project in
editable mode first.

The helper keeps idempotent semantics so repeated interpreter startups (e.g. within
tests) do not duplicate entries in ``sys.path``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Prepend the repository ``src`` directory to ``sys.path`` if missing."""
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    if src_dir.exists():
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_ensure_src_on_path()

