"""End-to-end tests asserting the SSE analysis stream contract."""

from __future__ import annotations

import asyncio
import json
import time
import types
from threading import Event
from typing import Any, AsyncIterator, Dict, List, Tuple

import pandas as pd
import pytest

from chart_mcp.config import settings
from chart_mcp.schemas.streaming import StepEventDetails, StepStartStreamPayload
from chart_mcp.utils import sse
from chart_mcp.utils.errors import UpstreamError


def _parse_event_names(raw: str) -> List[str]:
    """Extract SSE event names from the concatenated wire payload."""
    names: List[str] = []
    for line in raw.splitlines():
        if line.startswith("event: "):
            names.append(line.split("event: ", maxsplit=1)[1])
    return names


def _parse_events(raw: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Return ``(event_name, payload)`` pairs parsed from an SSE string."""

    events: List[Tuple[str, Dict[str, Any]]] = []
    for block in raw.split("\n\n"):
        if not block or block.startswith(":"):
            continue
        name: str | None = None
        payload_raw: str | None = None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line.split("event: ", maxsplit=1)[1]
            elif line.startswith("data: "):
                payload_raw = line.split("data: ", maxsplit=1)[1]
        if name is None or payload_raw is None:
            continue
        try:
            payload: Dict[str, Any] = json.loads(payload_raw)
        except json.JSONDecodeError:
            # Tests prefer failing loudly when payloads cannot be decoded, so the
            # helper keeps the raw string for assertions and debugging context.
            payload = {"raw": payload_raw}
        events.append((name, payload))
    return events


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

    events: List[tuple[str, str | None]] = []
    for block in body.split("\n\n"):
        if not block:
            continue
        event_name: str | None = None
        data_payload: str | None = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.split("event: ", 1)[1]
            elif line.startswith("data: "):
                data_payload = line.split("data: ", 1)[1]
        if event_name:
            events.append((event_name, data_payload))

    names = [name for name, _ in events]
    error_payloads = [payload for name, payload in events if name == "error"]

    assert "step:start" in names, "Expected pipeline stage start events"
    assert not error_payloads, f"Unexpected error events in stream: {error_payloads}"
    for expected_event in [
        "ohlcv",
        "range",
        "selected",
        "indicators",
        "levels",
        "patterns",
        "result_partial",
        "token",
        "result_final",
        "done",
    ]:
        assert expected_event in names, f"Missing streaming event: {expected_event}"
    assert names.index("ohlcv") < names.index("result_partial")
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


def test_sse_flow_handles_empty_dataset(client, monkeypatch):
    """Empty provider datasets should yield error + done events with context."""

    empty_frame = pd.DataFrame(columns=["ts", "o", "h", "l", "c", "v"])

    def _return_empty(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return empty_frame.copy()

    provider = client.app.state.streaming_service.provider
    monkeypatch.setattr(provider, "get_ohlcv", types.MethodType(_return_empty, provider))
    # Keep app.state.provider in sync so future services reusing it observe the stub.
    monkeypatch.setattr(client.app.state, "provider", provider)

    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 100}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        raw_body = "\n".join(response.iter_lines())

    events = _parse_events(raw_body)
    error_payload = next((payload for name, payload in events if name == "error"), None)
    done_payload = next((payload for name, payload in events if name == "done"), None)

    assert error_payload is not None, "Expected an error event when dataset is empty"
    assert error_payload["payload"]["code"] == "bad_request"
    assert done_payload is not None, "Stream should terminate with a done event"
    assert done_payload["payload"]["status"] == "error"
    assert done_payload["payload"]["code"] == "bad_request"


def test_sse_flow_reports_provider_failure(client, monkeypatch):
    """Provider exceptions must be surfaced as upstream errors in the stream."""

    def _raise_upstream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise UpstreamError("exchange down", details={"provider": "ccxt"})

    provider = client.app.state.streaming_service.provider
    monkeypatch.setattr(provider, "get_ohlcv", types.MethodType(_raise_upstream, provider))
    monkeypatch.setattr(client.app.state, "provider", provider)

    params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 50}
    with client.stream("GET", "/stream/analysis", params=params) as response:
        assert response.status_code == 200
        raw_body = "\n".join(response.iter_lines())

    events = _parse_events(raw_body)
    names = [name for name, _ in events]
    error_payload = next((payload for name, payload in events if name == "error"), None)
    done_payload = next((payload for name, payload in events if name == "done"), None)

    assert "result_final" not in names, "Final results should not be emitted after an error"
    assert error_payload is not None, "Error event should describe provider failure"
    assert error_payload["payload"]["code"] == "upstream_error"
    assert done_payload is not None
    assert done_payload["payload"]["status"] == "error"
    assert done_payload["payload"]["code"] == "upstream_error"
