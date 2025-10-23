"""Integration tests for SSE stream."""

from __future__ import annotations


def test_stream_analysis(client):
    with client.stream("GET", "/stream/analysis", params={"symbol": "BTCUSDT", "timeframe": "1h"}) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: tool_start" in body
    assert "event: result_final" in body
    assert "event: done" in body
