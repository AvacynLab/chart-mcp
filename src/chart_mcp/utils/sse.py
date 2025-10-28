"""Server-Sent Event utilities with heartbeat support."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import AsyncIterator, Iterable, TypedDict

from chart_mcp.config import settings
from chart_mcp.services.metrics import metrics
from chart_mcp.types import JSONValue

_HEARTBEAT_COMMENT = ": ping\n\n"
_STOP_SENTINEL = "__STOP__"


class SseEvent(TypedDict):
    """Typed representation of an outbound SSE packet."""

    event: str
    data: JSONValue


def format_sse(event: str, payload: JSONValue) -> str:
    """Format an SSE event using NDJSON payloads."""
    payload_ndjson = json.dumps(payload, separators=(",", ":"))
    return f"event: {event}\ndata: {payload_ndjson}\n\n"


async def heartbeat_sender(queue: "asyncio.Queue[str]") -> None:
    """Send heartbeat packets and comments at the configured interval."""
    interval = settings.stream_heartbeat_ms / 1000
    while True:
        await asyncio.sleep(interval)
        await queue.put(_HEARTBEAT_COMMENT)
        ts_ms = int(time.time() * 1000)
        await queue.put(format_sse("heartbeat", {"ts": ts_ms}))
        metrics.increment_stream_event("heartbeat")


class SseStreamer:
    """Utility orchestrating SSE emission with heartbeats."""

    def __init__(self) -> None:
        self._queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            raise RuntimeError("Heartbeat task already running for this streamer")
        self._heartbeat_task = asyncio.create_task(heartbeat_sender(self._queue))

    async def stop(self) -> None:
        """Stop the heartbeat task and signal stream termination."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
            self._heartbeat_task = None
        await self._queue.put(_STOP_SENTINEL)

    async def publish(self, event: str, payload: JSONValue) -> None:
        """Publish an SSE event to the internal queue."""
        metrics.increment_stream_event(event)
        await self._queue.put(format_sse(event, payload))

    async def stream(self) -> AsyncIterator[str]:
        """Yield SSE payloads until the stop sentinel is received."""
        while True:
            message = await self._queue.get()
            if message == _STOP_SENTINEL:
                break
            yield message


async def iter_events(events: Iterable[SseEvent]) -> AsyncIterator[str]:
    """Stream a finite list of events followed by a terminal marker."""
    for event in events:
        yield format_sse(event["event"], event["data"])
    yield format_sse("done", {})


__all__ = ["SseEvent", "SseStreamer", "format_sse", "heartbeat_sender", "iter_events"]
