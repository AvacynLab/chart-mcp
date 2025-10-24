"""Integration tests for market routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_ohlcv_success(client):
    response = client.get("/api/v1/market/ohlcv", params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert len(data["rows"]) == 50


def test_get_ohlcv_unauthorized(test_app):
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.get("/api/v1/market/ohlcv", params={"symbol": "BTCUSDT", "timeframe": "1h"})
        assert response.status_code == 401
