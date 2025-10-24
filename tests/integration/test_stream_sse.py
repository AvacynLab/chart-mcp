"""Integration tests for SSE stream."""

from __future__ import annotations


def test_stream_analysis(client):
    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 250}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: tool_start" in body
    assert "event: result_final" in body
    assert "event: done" in body


def test_stream_analysis_rejects_large_limit(client):
    response = client.get(
        "/stream/analysis",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 6000},
    )
    payload = response.json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "bad_request"
    assert "limit" in payload["error"]["message"].lower()


def test_stream_analysis_rejects_too_many_indicators(client):
    params = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "limit": 250,
        "indicators": [f"ema{i}" for i in range(12)],
    }
    response = client.get("/stream/analysis", params=params)
    payload = response.json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "bad_request"
    assert "indicators" in payload["error"]["message"].lower()
