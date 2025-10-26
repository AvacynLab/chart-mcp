"""Integration tests for analysis route."""

from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from chart_mcp.services.data_providers.base import MarketDataProvider


def test_analysis_summary(client):
    """Full analysis pipeline surfaces neutral summary and disclaimer."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicators": [{"name": "ema", "params": {"window": 20}}],
        "include_levels": True,
        "include_patterns": True,
    }
    response = client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    summary = data["summary"]
    assert "Analyse de" in summary
    assert "acheter" not in summary.lower()
    assert data["disclaimer"]


def test_analysis_summary_normalizes_symbol(client, monkeypatch):
    """Analysis endpoint normalises symbols before calling the provider."""
    provider = client.app.state.provider
    captured: dict[str, str] = {}

    original = provider.get_ohlcv

    def capture(symbol: str, timeframe: str, *, limit: int, start=None, end=None):  # type: ignore[override]
        captured["symbol"] = symbol
        return original(symbol, timeframe, limit=limit, start=start, end=end)

    monkeypatch.setattr(provider, "get_ohlcv", capture)

    payload = {
        "symbol": "ethusdt",
        "timeframe": "1h",
        "indicators": [],
        "include_levels": False,
        "include_patterns": False,
    }
    response = client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert captured["symbol"] == "ETH/USDT"
    assert body["symbol"] == "ETH/USDT"


def test_analysis_summary_requires_authorization(test_app):
    """Bearer token is mandatory for accessing the summary endpoint."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicators": [],
        "include_levels": False,
        "include_patterns": False,
    }
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 401


def test_analysis_summary_rejects_invalid_timeframe(client):
    """Invalid timeframe strings should return a normalized bad request error."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "7m",
        "indicators": [],
        "include_levels": False,
        "include_patterns": False,
    }
    response = client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "bad_request"
    assert "timeframe" in error["message"].lower()


def test_analysis_summary_requires_minimum_history(client, monkeypatch):
    """Analysis endpoint should reject providers returning short histories."""

    class TinyProvider(MarketDataProvider):
        def __init__(self) -> None:
            base = 1_700_000_000
            self.frame = pd.DataFrame(
                {
                    "ts": list(range(base, base + 100)),
                    "o": [100.0 + i * 0.01 for i in range(100)],
                    "h": [101.0 + i * 0.01 for i in range(100)],
                    "l": [99.0 + i * 0.01 for i in range(100)],
                    "c": [100.5 + i * 0.01 for i in range(100)],
                    "v": [50.0 + i for i in range(100)],
                }
            )
            self.client = type("Client", (), {"id": "tiny"})()

        def get_ohlcv(self, *_, **__) -> pd.DataFrame:  # type: ignore[override]
            return self.frame.copy()

    provider = TinyProvider()
    monkeypatch.setattr(client.app.state, "provider", provider)
    monkeypatch.setattr(client.app.state.streaming_service, "provider", provider)

    response = client.post(
        "/api/v1/analysis/summary",
        json={
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "indicators": [],
            "include_levels": False,
            "include_patterns": False,
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert "400" in payload["error"]["message"]
