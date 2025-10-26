"""Assertions covering invariants baked into the Dockerfile runtime environment."""

from __future__ import annotations

from pathlib import Path


def test_runtime_pythonpath_includes_install_site_packages() -> None:
    """Ensure the Docker image exposes builder-installed site-packages at runtime."""
    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")
    assert "/install/lib/python3.11/site-packages:/app/src" in dockerfile, (
        "The runtime image must expose third-party dependencies and the src tree via PYTHONPATH."
    )
