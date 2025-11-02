"""Integration assertions for the SSE analysis response headers."""

from __future__ import annotations

import asyncio

from chart_mcp.config import settings
from chart_mcp.utils import sse


def test_stream_analysis_headers_and_events(client, monkeypatch):
    """Validate that the HTTP layer exposes the expected SSE headers/events.

    The test forces the heartbeat coroutine to emit immediately so the stream
    produces a deterministic sequence during the short-lived request. This
    keeps the assertions resilient while covering the heartbeat/metric events
    that must be present for the frontend to stay responsive.
    """
    monkeypatch.setattr(settings, "stream_heartbeat_ms", 100)

    async def immediate_heartbeat(queue):  # type: ignore[no-untyped-def]
        """Inject the first heartbeat instantly to keep the stream deterministic."""
        await queue.put(": ping\n\n")
        await queue.put(sse.format_sse("heartbeat", {"ts": 1}))
        while True:
            await asyncio.sleep(0.1)

    monkeypatch.setattr(sse, "heartbeat_sender", immediate_heartbeat)
    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 200}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        # The HTTP layer must expose the canonical SSE headers so reverse proxies
        # and browsers do not buffer the stream.
        content_type = response.headers.get("Content-Type")
        assert content_type is not None and content_type.startswith("text/event-stream")
        assert response.headers.get("Cache-Control") == "no-cache"
        assert response.headers.get("Connection") == "keep-alive"
        assert response.headers.get("X-Accel-Buffering") == "no"
        payload = "\n".join(response.iter_lines())

    assert "event: token" in payload or "event: result_partial" in payload
    assert "event: metric" in payload
    assert "event: heartbeat" in payload
    assert ": ping" in payload
