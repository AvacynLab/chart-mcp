"""Integration tests for analysis route."""

from __future__ import annotations


def test_analysis_summary(client):
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
