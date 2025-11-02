"""Integration coverage ensuring the SSE stream shuts down on disconnect."""

from __future__ import annotations

import asyncio
import types

import pytest

from chart_mcp.utils import sse


@pytest.mark.anyio
async def test_stream_analysis_cleans_up_on_disconnect(client, monkeypatch):
    """Disconnecting the HTTP client must trigger iterator shutdown hooks."""
    shutdown_event = asyncio.Event()
    stub_holder: dict[str, "StubStream"] = {}

    class StubStream:
        """Async iterator emulating the streaming pipeline contract."""

        def __init__(self) -> None:
            self._emitted = False
            self.aclose_called = False
            self.stop_called = False

        def __aiter__(self) -> "StubStream":
            return self

        async def __anext__(self) -> str:
            if self.aclose_called or self.stop_called:
                raise StopAsyncIteration
            if not self._emitted:
                self._emitted = True
                return sse.format_sse(
                    "step:start",
                    {"payload": {"stage": "ohlcv", "description": "stub", "metadata": {}}},
                )
            await asyncio.sleep(0.05)
            return sse.format_sse("heartbeat", {"ts": 1})

        async def aclose(self) -> None:
            self.aclose_called = True
            shutdown_event.set()

        async def stop(self) -> None:
            self.stop_called = True
            shutdown_event.set()

    async def fake_stream_analysis(self, *args, **kwargs):  # type: ignore[unused-arg]
        stub = StubStream()
        stub_holder["stream"] = stub
        return stub

    streaming_service = client.app.state.streaming_service
    monkeypatch.setattr(
        streaming_service,
        "stream_analysis",
        types.MethodType(fake_stream_analysis, streaming_service),
    )

    from starlette.requests import Request

    call_counter = {"value": 0}

    async def fake_is_disconnected(self) -> bool:  # type: ignore[override]
        call_counter["value"] += 1
        return call_counter["value"] > 1

    monkeypatch.setattr(Request, "is_disconnected", fake_is_disconnected)

    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50}

    def consume_once() -> None:
        with client.stream("GET", "/stream/analysis", params=params) as response:
            iterator = response.iter_lines()
            next(iterator)

    await asyncio.to_thread(consume_once)
    await asyncio.wait_for(shutdown_event.wait(), timeout=1.0)

    stub = stub_holder["stream"]
    # Both hooks must be triggered so upstream jobs halt and release resources.
    assert stub.aclose_called
    assert stub.stop_called
