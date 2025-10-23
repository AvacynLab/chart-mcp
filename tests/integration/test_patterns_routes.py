"""Integration tests for pattern routes."""

from __future__ import annotations


def test_patterns_route(client):
    response = client.get("/api/v1/patterns", params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert isinstance(data["patterns"], list)
