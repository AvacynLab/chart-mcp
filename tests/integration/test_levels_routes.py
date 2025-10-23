"""Integration tests for levels routes."""

from __future__ import annotations


def test_levels_route(client):
    response = client.get("/api/v1/levels", params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert isinstance(data["levels"], list)
