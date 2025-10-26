"""Integration tests for pattern routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_patterns_route(client):
    """Pattern discovery returns normalized symbols and iterable payloads."""
    response = client.get(
        "/api/v1/patterns",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 150},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC/USDT"
    assert data["source"] == "stub"
    assert isinstance(data["patterns"], list)


def test_patterns_route_requires_authorization(test_app):
    """Unauthorized callers must be denied access to pattern detection."""
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.get(
            "/api/v1/patterns",
            params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50},
        )
    assert response.status_code == 401


def test_patterns_route_rejects_invalid_timeframe(client):
    """An invalid timeframe should propagate as a bad request response."""
    response = client.get(
        "/api/v1/patterns",
        params={"symbol": "BTCUSDT", "timeframe": "7m", "limit": 50},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "bad_request"
    assert "timeframe" in error["message"].lower()
