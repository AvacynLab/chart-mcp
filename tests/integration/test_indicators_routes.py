"""Integration tests for indicator routes."""

from __future__ import annotations


def test_compute_indicator(client):
    payload = {"symbol": "BTCUSDT", "timeframe": "1h", "indicator": "ema", "params": {"window": 10}, "limit": 100}
    response = client.post("/api/v1/indicators/compute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["symbol"] == "BTC/USDT"
    assert data["meta"]["timeframe"] == "1h"
    assert data["meta"]["indicator"] == "ema"
    assert len(data["series"]) > 0
