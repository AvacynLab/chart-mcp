"""Integration tests for levels routes."""

from __future__ import annotations


def test_levels_route(client):
    response = client.get("/api/v1/levels", params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC/USDT"
    assert isinstance(data["levels"], list)


def test_levels_route_respects_max_parameter(client):
    response = client.get(
        "/api/v1/levels",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150, "max": 2},
    )
    assert response.status_code == 200
    data = response.json()
    strengths = [level["strength"] for level in data["levels"]]
    assert len(strengths) <= 2
    assert strengths == sorted(strengths, reverse=True)
