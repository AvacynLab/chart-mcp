"""Unit tests for the streaming service error handling safeguards."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Iterable, Mapping, Optional

import pandas as pd
import pytest

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelCandidate, LevelsService
from chart_mcp.services.patterns import PatternResult, PatternsService
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import BadRequest


class _FailingProvider(MarketDataProvider):
    """Provider double used to trigger controlled failures in the pipeline."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def get_ohlcv(  # type: ignore[override]
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> pd.DataFrame:
        raise self._error


class _DummyLevels(LevelsService):
    """No-op levels detector returning an empty candidate list."""

    def detect_levels(self, frame: pd.DataFrame) -> list[LevelCandidate]:  # type: ignore[override]
        return []


class _DummyPatterns(PatternsService):
    """No-op pattern detector returning an empty result list."""

    def detect(self, frame: pd.DataFrame) -> list[PatternResult]:  # type: ignore[override]
        return []


class _DummyLLM(AnalysisLLMService):
    """LLM stub returning a predictable textual summary."""

    def summarize(  # type: ignore[override]
        self,
        symbol: str,
        timeframe: str,
        indicator_highlights: Mapping[str, float],
        levels: Iterable[LevelCandidate],
        patterns: Iterable[PatternResult],
    ) -> str:
        return "Stub summary"


def _build_streaming_service(error: Exception) -> StreamingService:
    """Helper constructing a streaming service wired with deterministic doubles."""

    provider = _FailingProvider(error)
    indicators = IndicatorService()
    levels = _DummyLevels()
    patterns = _DummyPatterns()
    llm = _DummyLLM()
    return StreamingService(provider, indicators, levels, patterns, llm)


async def _collect_events(iterator: AsyncIterator[str]) -> list[str]:
    """Drain an asynchronous iterator into a list of raw SSE payloads."""

    events: list[str] = []
    async for chunk in iterator:
        events.append(chunk)
    return events


def _parse_events(raw_events: Iterable[str]) -> list[tuple[str, dict]]:
    """Extract the event name and NDJSON payload from the SSE stream."""

    parsed: list[tuple[str, dict]] = []
    for chunk in raw_events:
        # Heartbeat comments start with ':' and can be ignored for assertions.
        lines = [line for line in chunk.splitlines() if line and not line.startswith(":")]
        if len(lines) < 2:
            continue
        event = lines[0].split("event: ", maxsplit=1)[1]
        data = json.loads(lines[1].split("data: ", maxsplit=1)[1])
        parsed.append((event, data))
    return parsed


@pytest.mark.anyio
async def test_stream_analysis_surfaces_api_errors_without_crashing() -> None:
    """Ensure domain errors result in structured `error` events followed by completion."""

    service = _build_streaming_service(BadRequest("Symbol must be provided"))

    raw = await asyncio.wait_for(
        _collect_events(service.stream_analysis("BTCUSD", "1d", [])), timeout=1.0
    )
    events = _parse_events(raw)

    expected_error = (
        "error",
        {"type": "error", "payload": {"code": "bad_request", "message": "Symbol must be provided"}},
    )
    assert expected_error in events
    # The pipeline should still emit a terminal "done" event so the client can tidy up UI state.
    assert any(
        event == "done" and data.get("payload", {}).get("code") == "bad_request"
        for event, data in events
    )


@pytest.mark.anyio
async def test_stream_analysis_handles_unexpected_exceptions_gracefully() -> None:
    """Unexpected exceptions should be logged and surfaced as generic internal errors."""

    service = _build_streaming_service(RuntimeError("network down"))

    raw = await asyncio.wait_for(
        _collect_events(service.stream_analysis("ETHUSD", "1h", [])), timeout=1.0
    )
    events = _parse_events(raw)

    expected_error = (
        "error",
        {"type": "error", "payload": {"code": "internal_error", "message": "Streaming pipeline failed"}},
    )
    assert expected_error in events
    # The consumer still receives the closing marker which avoids dangling EventSource connections.
    assert any(
        event == "done" and data.get("payload", {}).get("code") == "internal_error"
        for event, data in events
    )


@pytest.mark.anyio
async def test_stream_analysis_rejects_invalid_limit() -> None:
    """The streaming service should reject unbounded ``limit`` values upfront."""

    service = _build_streaming_service(RuntimeError("should not reach provider"))
    iterator = service.stream_analysis("BTCUSD", "1h", [], limit=6001)

    with pytest.raises(BadRequest, match="limit must be between 1 and 5000"):
        await anext(iterator)
