"""Integration tests for levels routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_levels_route(client):
    """Levels endpoint returns normalized symbols and structured payloads."""
    response = client.get(
        "/api/v1/levels",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC/USDT"
    assert isinstance(data["levels"], list)


def test_levels_route_respects_max_parameter(client):
    """The optional `max` query parameter limits and sorts the returned levels."""
    response = client.get(
        "/api/v1/levels",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150, "max": 2},
    )
    assert response.status_code == 200
    data = response.json()
    strengths = [level["strength"] for level in data["levels"]]
    assert len(strengths) <= 2
    assert strengths == sorted(strengths, reverse=True)


def test_levels_route_requires_authorization(test_app):
    """Missing credentials must result in a 401 error."""
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.get(
            "/api/v1/levels",
            params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50},
        )
    assert response.status_code == 401


def test_levels_route_rejects_invalid_timeframe(client):
    """Invalid timeframe strings should surface as API-level bad requests."""
    response = client.get(
        "/api/v1/levels",
        params={"symbol": "BTCUSDT", "timeframe": "7m", "limit": 50},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "bad_request"
    assert "timeframe" in error["message"].lower()
