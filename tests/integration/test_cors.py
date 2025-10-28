"""Integration tests covering the CORS middleware contract."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from chart_mcp import app as app_module
from chart_mcp.config import Settings


def test_preflight_request_allows_configured_origin(test_app) -> None:  # noqa: ANN001
    """OPTIONS preflight should echo the allowed origin and headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,x-session-user",
    }
    params = {"symbol": "BTCUSDT", "timeframe": "1h"}
    with TestClient(test_app) as client:
        response = client.options("/api/v1/market/ohlcv", headers=headers, params=params)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "x-session-user" in allow_headers
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_preflight_rejects_unlisted_origin(test_app) -> None:  # noqa: ANN001
    """Origins outside the configured allowlist should not receive CORS headers."""
    headers = {
        "Origin": "https://malicious.example",  # not present in ALLOWED_ORIGINS
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,x-session-user",
    }
    params = {"symbol": "BTCUSDT", "timeframe": "1h"}
    with TestClient(test_app) as client:
        response = client.options("/api/v1/market/ohlcv", headers=headers, params=params)
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_create_app_fails_without_origins_in_production(monkeypatch) -> None:  # noqa: ANN001
    """Production-like settings without CORS origins should abort application startup."""
    dummy_settings = Settings(
        API_TOKEN="prod-token-123",
        ALLOWED_ORIGINS="",
        PLAYWRIGHT=False,
        FEATURE_FINANCE=True,
    )
    monkeypatch.setattr(app_module, "get_settings", lambda: dummy_settings)
    with pytest.raises(RuntimeError) as exc:
        app_module.create_app()
    assert "ALLOWED_ORIGINS" in str(exc.value)
    # Restore the cached module-level app to avoid side effects on subsequent tests.
    importlib.reload(app_module)
