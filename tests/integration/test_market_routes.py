"""Integration tests for market routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_ohlcv_success(client):
    response = client.get("/api/v1/market/ohlcv", params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC/USDT"
    assert len(data["rows"]) == 50


def test_get_ohlcv_unauthorized(test_app):
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.get("/api/v1/market/ohlcv", params={"symbol": "BTCUSDT", "timeframe": "1h"})
        assert response.status_code == 401


def test_get_ohlcv_rejects_invalid_time_range(client):
    response = client.get(
        "/api/v1/market/ohlcv",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "start": 200, "end": 100},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert "greater than" in payload["error"]["message"]


def test_get_ohlcv_rejects_unsupported_timeframe(client):
    response = client.get(
        "/api/v1/market/ohlcv",
        params={"symbol": "BTCUSDT", "timeframe": "7m"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
