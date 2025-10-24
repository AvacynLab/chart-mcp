"""Integration tests validating the rate limiting middleware."""

from __future__ import annotations

from importlib import reload

from fastapi.testclient import TestClient

import chart_mcp.app as app_module
import chart_mcp.config as config_module


def test_rate_limit_enforced(monkeypatch):
    """Requests exceeding the configured quota should return HTTP 429."""

    monkeypatch.setenv("API_TOKEN", "ratelimit-token")
    monkeypatch.setenv("PLAYWRIGHT", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")

    # Reload the settings module so the lru_cache observes the overridden env.
    config_module.get_settings.cache_clear()
    reload(config_module)
    reload(app_module)

    app = app_module.create_app()

    with TestClient(app) as client:
        first = client.get("/health")
        assert first.status_code == 200
        assert first.headers["X-RateLimit-Remaining"] == "1"

        second = client.get("/health")
        assert second.status_code == 200
        assert second.headers["X-RateLimit-Remaining"] == "0"

        third = client.get("/health")
        assert third.status_code == 429
        assert third.headers["X-RateLimit-Remaining"] == "0"
        payload = third.json()
        assert payload["error"]["code"] == "too_many_requests"

    # Clear the settings cache so subsequent tests recreate the application with
    # the standard testing configuration managed by ``conftest``.
    config_module.get_settings.cache_clear()
