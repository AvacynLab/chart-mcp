"""Helpers to produce Server-Sent Events compatible with Vercel SDK."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, AsyncIterator, Dict, Iterable

from chart_mcp.config import settings

_HEARTBEAT_COMMENT = ": ping\n\n"
_STOP_SENTINEL = "__STOP__"


def format_sse(event: str, payload: Dict[str, Any]) -> str:
    """Format a SSE event using NDJSON payload."""

    return f"event: {event}\ndata: {json.dumps(payload, separators=(",", ":"))}\n\n"


async def heartbeat_sender(queue: "asyncio.Queue[str]") -> None:
    """Send heartbeat comments at a configured interval."""

    interval = settings.stream_heartbeat_ms / 1000
    while True:
        await asyncio.sleep(interval)
        await queue.put(_HEARTBEAT_COMMENT)


class SseStreamer:
    """Utility orchestrating SSE emission with heartbeats."""

    def __init__(self) -> None:
        self._queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start background heartbeat task."""

        self._heartbeat_task = asyncio.create_task(heartbeat_sender(self._queue))

    async def stop(self) -> None:
        """Stop heartbeat task and signal stream termination."""

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        await self._queue.put(_STOP_SENTINEL)

    async def publish(self, event: str, payload: Dict[str, Any]) -> None:
        """Publish a SSE event to the internal queue."""

        await self._queue.put(format_sse(event, payload))

    async def stream(self) -> AsyncIterator[str]:
        """Yield SSE payloads until the stop sentinel is received."""

        while True:
            message = await self._queue.get()
            if message == _STOP_SENTINEL:
                break
            yield message


async def iter_events(events: Iterable[Dict[str, Any]]) -> AsyncIterator[str]:
    """Convenience helper to stream a finite list of events."""

    for event in events:
        yield format_sse(event["event"], event["data"])
    yield format_sse("done", {})
