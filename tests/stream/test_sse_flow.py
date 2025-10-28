"""End-to-end tests asserting the SSE analysis stream contract."""

from __future__ import annotations

import asyncio
import time
import types
from threading import Event
from typing import Any, AsyncIterator, Dict, List

import pytest

from chart_mcp.config import settings
from chart_mcp.schemas.streaming import StepEventDetails, StepStartStreamPayload
from chart_mcp.utils import sse


def _parse_event_names(raw: str) -> List[str]:
    """Extract SSE event names from the concatenated wire payload."""
    names: List[str] = []
    for line in raw.splitlines():
        if line.startswith("event: "):
            names.append(line.split("event: ", maxsplit=1)[1])
    return names


def test_sse_flow_event_sequence(client, monkeypatch):
    """Ensure the SSE endpoint emits the expected heartbeat and stage events."""
    monkeypatch.setattr(settings, "stream_heartbeat_ms", 50)

    async def immediate_heartbeat(queue):  # type: ignore[no-untyped-def]
        """Inject a first heartbeat immediately to guarantee coverage."""
        await queue.put(": ping\n\n")
        await queue.put(sse.format_sse("heartbeat", {"ts": int(time.time() * 1000)}))
        while True:
            await asyncio.sleep(0.05)

    monkeypatch.setattr(sse, "heartbeat_sender", immediate_heartbeat)

    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 120}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())

    names = _parse_event_names(body)
    assert "step:start" in names, "Expected pipeline stage start events"
    assert "result_partial" in names
    assert "token" in names
    assert "result_final" in names
    assert names.index("step:start") < names.index("result_final")
    assert names.index("result_final") < names.index("done")
    assert "heartbeat" in names, "Heartbeat events keep the stream alive"


@pytest.mark.anyio
async def test_sse_flow_cancels_on_disconnect(client, monkeypatch):
    """Disconnecting the client should trigger the streaming job shutdown hooks."""
    stop_flag = Event()

    class StubStream(AsyncIterator[str]):
        """Async iterator emulating a long-running streaming pipeline."""

        def __init__(self) -> None:
            self.emitted = False
            self.stop_called = False

        def __aiter__(self) -> "StubStream":
            return self

        async def __anext__(self) -> str:
            if self.stop_called:
                raise StopAsyncIteration
            if not self.emitted:
                self.emitted = True
                payload = StepStartStreamPayload(
                    type="step:start",
                    payload=StepEventDetails(stage="ohlcv", description="stub", metadata={}),
                )
                return sse.format_sse("step:start", payload.model_dump())
            await asyncio.sleep(0.05)
            return sse.format_sse("heartbeat", {"ts": int(time.time() * 1000)})

        async def aclose(self) -> None:
            self.stop_called = True
            stop_flag.set()

        async def stop(self) -> None:
            self.stop_called = True
            stop_flag.set()

    async def fake_stream_analysis(self, *args: Any, **kwargs: Dict[str, Any]) -> StubStream:
        return StubStream()

    streaming_service = client.app.state.streaming_service
    monkeypatch.setattr(
        streaming_service,
        "stream_analysis",
        types.MethodType(fake_stream_analysis, streaming_service),
    )

    from starlette.requests import Request

    call_count = {"value": 0}

    async def fake_is_disconnected(self) -> bool:  # type: ignore[override]
        call_count["value"] += 1
        return call_count["value"] > 1

    monkeypatch.setattr(Request, "is_disconnected", fake_is_disconnected)

    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50}

    def _consume_once() -> None:
        with client.stream("GET", "/stream/analysis", params=params) as response:
            iterator = response.iter_lines()
            next(iterator)

    await asyncio.to_thread(_consume_once)
    assert stop_flag.wait(timeout=1.0), "Streaming job should be stopped on disconnect"
