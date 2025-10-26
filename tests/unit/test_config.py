"""Tests for the application settings helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chart_mcp.config import Settings


def test_empty_env_token_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure blank ``API_TOKEN`` entries fall back to the default development token."""
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("API_TOKEN", "")
    settings = Settings()
    assert settings.api_token == "dev-token"


def test_short_token_still_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short tokens should continue to raise validation errors to enforce security."""
    monkeypatch.setenv("API_TOKEN", "short")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.delenv("API_TOKEN", raising=False)
