"""Integration tests for indicator routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_compute_indicator(client):
    """Indicators endpoint returns normalized metadata and non-empty series."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicator": "ema",
        "params": {"window": 10},
        "limit": 100,
    }
    response = client.post("/api/v1/indicators/compute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["symbol"] == "BTC/USDT"
    assert data["meta"]["timeframe"] == "1h"
    assert data["meta"]["indicator"] == "ema"
    assert len(data["series"]) > 0


def test_compute_indicator_requires_authorization(test_app):
    """Requests without the bearer token must be rejected with 401."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicator": "ema",
        "params": {"window": 10},
        "limit": 20,
    }
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.post("/api/v1/indicators/compute", json=payload)
    assert response.status_code == 401


def test_compute_indicator_rejects_unknown_indicator(client):
    """An unsupported indicator name should return a validation error payload."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicator": "foobar",
        "params": {},
        "limit": 50,
    }
    response = client.post("/api/v1/indicators/compute", json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    details = response.json()["details"]
    # At least one detail entry must mention the unsupported indicator value.
    assert any("unsupported indicator" in str(detail).lower() for detail in details)
