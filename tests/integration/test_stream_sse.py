"""Integration tests for SSE stream."""

from __future__ import annotations

from chart_mcp.utils import sse


def test_stream_analysis(client):
    """Stream emits events in order from step:start to result_final to done."""
    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 250}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    start_idx = body.index("event: step:start")
    final_idx = body.index("event: result_final")
    done_idx = body.index("event: done")
    assert start_idx < final_idx < done_idx


def test_stream_analysis_rejects_large_limit(client):
    """Upper bound guard on the limit parameter returns a bad request error."""
    response = client.get(
        "/stream/analysis",
        params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 6000},
    )
    payload = response.json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "bad_request"
    assert "limit" in payload["error"]["message"].lower()


def test_stream_analysis_rejects_too_many_indicators(client):
    """More than ten indicators are rejected to keep SSE payloads bounded."""
    params = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "limit": 250,
        "indicators": ",".join(f"ema{i}" for i in range(12)),
    }
    response = client.get("/stream/analysis", params=params)
    payload = response.json()
    assert response.status_code == 400
    assert payload["error"]["code"] == "bad_request"
    assert "indicators" in payload["error"]["message"].lower()


def test_stream_analysis_deduplicates_indicator_specs(client, monkeypatch):
    """Duplicate indicator specs are collapsed before invoking the service."""
    streaming_service = client.app.state.streaming_service
    captured: dict[str, object] = {}

    async def fake_stream_analysis(
        symbol: str,
        timeframe: str,
        indicator_specs,
        **kwargs,
    ):
        captured["symbol"] = symbol
        captured["indicators"] = indicator_specs
        captured["max_levels"] = kwargs.get("max_levels")

        async def generator():
            yield sse.format_sse("heartbeat", {"ts": 42})

        return generator()

    monkeypatch.setattr(streaming_service, "stream_analysis", fake_stream_analysis)

    params = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "indicators": (
            "ema:21, EMA:21 , ema : window = 21 , "
            "rsi:14, RSI:14 , "
            "macd:fast=12;slow=26;signal=9, MACD:FAST=12;SLOW=26;SIGNAL=9"
        ),
        "max": 7,
    }

    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        # Drain the response to ensure the async generator runs to completion.
        list(response.iter_text())

    expected = [
        {"name": "ema", "params": {"window": 21.0}},
        {"name": "rsi", "params": {"window": 14.0}},
        {"name": "macd", "params": {"fast": 12.0, "slow": 26.0, "signal": 9.0}},
    ]
    assert captured["indicators"] == expected
    assert captured["max_levels"] == 7
