"""Tests for the maintenance cleanup CLI helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from chart_mcp.cli.cleanup import DEFAULT_TARGETS, clean_worktree, main


@pytest.mark.parametrize("target", DEFAULT_TARGETS)
def test_clean_worktree_removes_default_targets(tmp_path: Path, target: str) -> None:
    """The helper should delete each default artefact directory when present."""

    artefact = tmp_path / target
    artefact.mkdir()
    removed = clean_worktree(tmp_path, [target])
    assert artefact not in removed or not artefact.exists()
    assert not artefact.exists()


def test_clean_worktree_ignores_entries_outside_base(tmp_path: Path) -> None:
    """Entries traversing outside the base directory must never be removed."""

    outside = tmp_path.parent / "rogue"
    outside.mkdir()
    removed = clean_worktree(tmp_path, ["../rogue"])
    assert outside.exists()
    assert removed == []


def test_cli_main_handles_custom_paths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI should report removed paths and respect the provided base directory."""

    custom = tmp_path / "custom-cache"
    custom.mkdir()
    exit_code = main(["--base", str(tmp_path), "custom-cache"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "custom-cache" in captured.out
    assert not custom.exists()


def test_cli_main_reports_clean_workspace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """When nothing is removed the CLI should emit an informative message."""

    exit_code = main(["--base", str(tmp_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "already clean" in captured.out
