"""Integration tests covering the FEATURE_FINANCE flag behaviour."""

from __future__ import annotations

import importlib
from datetime import timezone

from fastapi.testclient import TestClient

from chart_mcp import app as app_module
from chart_mcp.config import get_settings
from chart_mcp.services import finance as finance_module


def test_finance_routes_disabled(monkeypatch) -> None:
    """Ensure finance endpoints are not mounted when the feature flag is false."""
    # Configure the environment to mimic an operator disabling finance artefacts for
    # a lightweight deployment. The cache is cleared so the new values are picked up
    # by the settings factory before instantiating the application.
    monkeypatch.setenv("API_TOKEN", "testingtoken")
    monkeypatch.setenv("PLAYWRIGHT", "true")
    monkeypatch.setenv("FEATURE_FINANCE", "false")
    get_settings.cache_clear()

    # Reload the FastAPI factory module so its module-level ``settings`` singleton
    # reflects the freshly configured environment variables before building the app.
    importlib.reload(app_module)
    app = app_module.create_app()
    with TestClient(app) as client:
        client.headers.update(
            {"Authorization": "Bearer testingtoken", "X-User-Type": "regular"}
        )
        response = client.get("/api/v1/finance/quote", params={"symbol": "BTCUSD"})
        assert response.status_code == 404

    # Reset the settings cache so subsequent tests restore the default "true" flag
    # injected by the shared fixtures in ``tests.conftest``. We also reload the
    # module with the feature flag toggled back on so the module-level ``app``
    # instance matches the default behaviour expected by the rest of the suite.
    monkeypatch.setenv("FEATURE_FINANCE", "true")
    get_settings.cache_clear()
    importlib.reload(app_module)


def test_finance_routes_enabled_smoke(monkeypatch) -> None:
    """Finance flag on should expose read-only routes responding successfully."""
    monkeypatch.setenv("API_TOKEN", "testingtoken")
    monkeypatch.setenv("FEATURE_FINANCE", "true")
    monkeypatch.setenv("PLAYWRIGHT", "true")
    get_settings.cache_clear()
    importlib.reload(app_module)
    app = app_module.create_app()
    with TestClient(app) as client:
        client.headers.update(
            {
                "Authorization": "Bearer testingtoken",
                "X-User-Type": "regular",
            }
        )
        response = client.get(
            "/api/v1/finance/quote", params={"symbol": "BTCUSD"}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["symbol"] == "BTCUSD"
        assert "price" in payload and "currency" in payload
        assert "updatedAt" in payload and payload["updatedAt"]
    get_settings.cache_clear()
    importlib.reload(app_module)


def test_finance_service_freezes_clock_in_playwright(monkeypatch) -> None:
    """Playwright mode should wire deterministic timestamps into finance data."""
    monkeypatch.setenv("API_TOKEN", "testingtoken")
    monkeypatch.setenv("FEATURE_FINANCE", "true")
    monkeypatch.setenv("PLAYWRIGHT", "true")
    get_settings.cache_clear()
    importlib.reload(app_module)
    app = app_module.create_app()
    finance_service = app.state.finance_service
    assert finance_service is not None
    snapshot = finance_service.get_quote("BTCUSD")
    assert snapshot.updated_at == finance_module.PLAYWRIGHT_REFERENCE_TIME
    news_article = finance_service.get_news("NVDA", limit=1)[0]
    assert news_article.published_at.tzinfo == timezone.utc
    get_settings.cache_clear()
    importlib.reload(app_module)


def test_finance_service_uses_realtime_clock_when_not_playwright(monkeypatch) -> None:
    """Disabling Playwright mode should fall back to the actual wall clock."""
    monkeypatch.setenv("API_TOKEN", "testingtoken")
    monkeypatch.setenv("FEATURE_FINANCE", "true")
    monkeypatch.setenv("PLAYWRIGHT", "false")
    get_settings.cache_clear()
    importlib.reload(app_module)
    app = app_module.create_app()
    finance_service = app.state.finance_service
    assert finance_service is not None
    snapshot = finance_service.get_quote("BTCUSD")
    delta = abs(
        (snapshot.updated_at - finance_module.PLAYWRIGHT_REFERENCE_TIME).total_seconds()
    )
    # With the realtime clock the difference should be comfortably larger than a minute.
    assert delta > 60
    assert snapshot.updated_at.tzinfo == timezone.utc
    get_settings.cache_clear()
    importlib.reload(app_module)
