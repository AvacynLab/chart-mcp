"""Integration tests for analysis route."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_analysis_summary(client):
    """Full analysis pipeline surfaces neutral summary and disclaimer."""
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


def test_analysis_summary_requires_authorization(test_app):
    """Bearer token is mandatory for accessing the summary endpoint."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicators": [],
        "include_levels": False,
        "include_patterns": False,
    }
    with TestClient(test_app) as unauthorized_client:
        response = unauthorized_client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 401


def test_analysis_summary_rejects_invalid_timeframe(client):
    """Invalid timeframe strings should return a normalized bad request error."""
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "7m",
        "indicators": [],
        "include_levels": False,
        "include_patterns": False,
    }
    response = client.post("/api/v1/analysis/summary", json=payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "bad_request"
    assert "timeframe" in error["message"].lower()
