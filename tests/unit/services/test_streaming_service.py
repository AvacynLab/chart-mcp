"""Unit tests for the streaming service error handling safeguards."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Iterable, Mapping, Optional

import pandas as pd
import pytest

from chart_mcp.services.analysis_llm import AnalysisLLMService, AnalysisSummary
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelCandidate, LevelsService
from chart_mcp.services.patterns import PatternResult, PatternsService
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import BadRequest


class _StaticProvider(MarketDataProvider):
    """Provider returning deterministic OHLCV rows for cancellation tests."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def get_ohlcv(  # type: ignore[override]
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> pd.DataFrame:
        return self._frame.head(limit).copy()


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


class _FailingIndicator(IndicatorService):
    """Indicator stub raising :class:`BadRequest` to simulate invalid params."""

    def compute(  # type: ignore[override]
        self,
        frame: pd.DataFrame,
        indicator: str,
        params: Mapping[str, float],
    ) -> pd.DataFrame:
        raise BadRequest("Indicator parameters invalid")


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
    ) -> AnalysisSummary:
        return AnalysisSummary(
            summary="Stub summary",
            disclaimer=AnalysisLLMService.disclaimer,
        )


def _build_streaming_service(error: Exception) -> StreamingService:
    """Construct a streaming service wired with deterministic doubles."""
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
async def test_stream_analysis_iterator_exposes_stop_hook() -> None:
    """The asynchronous iterator should surface a ``stop`` coroutine for cleanup."""
    frame = pd.DataFrame(
        {
            "ts": [1, 2, 3, 4, 5],
            "o": [10.0, 10.2, 10.4, 10.6, 10.8],
            "h": [10.5, 10.7, 10.9, 11.1, 11.3],
            "l": [9.5, 9.7, 9.9, 10.1, 10.3],
            "c": [10.1, 10.3, 10.5, 10.7, 10.9],
            "v": [100, 110, 120, 130, 140],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )
    iterator = await service.stream_analysis("BTCUSDT", "1h", [], limit=3)

    # Pull a first chunk to make sure the background pipeline is running.
    first_chunk = await asyncio.wait_for(anext(iterator), timeout=1.0)
    assert first_chunk.startswith("event:")

    assert hasattr(iterator, "stop")
    stopper = iterator.stop  # type: ignore[attr-defined]
    assert callable(stopper)

    await iterator.aclose()
    await asyncio.wait_for(stopper(), timeout=1.0)


@pytest.mark.anyio
async def test_stream_analysis_surfaces_api_errors_without_crashing() -> None:
    """Ensure domain errors result in structured `error` events followed by completion."""
    service = _build_streaming_service(BadRequest("Symbol must be provided"))

    iterator = await service.stream_analysis("BTCUSD", "1d", [])
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
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

    iterator = await service.stream_analysis("ETHUSD", "1h", [])
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    events = _parse_events(raw)

    expected_error = (
        "error",
        {
            "type": "error",
            "payload": {"code": "internal_error", "message": "Streaming pipeline failed"},
        },
    )
    assert expected_error in events
    # The consumer still receives the closing marker which avoids dangling EventSource connections.
    assert any(
        event == "done" and data.get("payload", {}).get("code") == "internal_error"
        for event, data in events
    )


@pytest.mark.anyio
async def test_stream_analysis_indicator_errors_surface_as_bad_request() -> None:
    """Indicator validation issues should propagate as structured error events."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 8)),
            "o": [float(v) for v in range(1, 8)],
            "h": [float(v) + 0.3 for v in range(1, 8)],
            "l": [float(v) - 0.3 for v in range(1, 8)],
            "c": [float(v) for v in range(1, 8)],
            "v": [100 + v for v in range(7)],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        _FailingIndicator(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )

    iterator = await service.stream_analysis(
        "BTCUSDT", "1h", [{"name": "ema", "params": {"window": 21}}], limit=7
    )
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    events = _parse_events(raw)
    error_payload = {
        "type": "error",
        "payload": {"code": "bad_request", "message": "Indicator parameters invalid"},
    }

    assert ("error", error_payload) in events
    assert any(
        event == "done" and data.get("payload", {}).get("code") == "bad_request"
        for event, data in events
    ), "The stream should close with a done event referencing the error code"
    assert not any(event == "result_final" for event, _ in events)


@pytest.mark.anyio
async def test_stream_analysis_rejects_invalid_limit() -> None:
    """The streaming service should reject unbounded ``limit`` values upfront."""
    service = _build_streaming_service(RuntimeError("should not reach provider"))
    with pytest.raises(BadRequest, match="limit must be between 1 and 5000"):
        await service.stream_analysis("BTCUSD", "1h", [], limit=6001)


@pytest.mark.anyio
async def test_stream_analysis_emits_metric_events_for_every_stage() -> None:
    """The SSE stream should expose timing metrics for each pipeline step."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 41)),
            "o": [float(v) for v in range(1, 41)],
            "h": [float(v) + 0.5 for v in range(1, 41)],
            "l": [float(v) - 0.5 for v in range(1, 41)],
            "c": [float(v) for v in range(1, 41)],
            "v": [100 + v for v in range(40)],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )
    specs = [{"name": "ma", "params": {"window": 3}}]

    iterator = await service.stream_analysis("BTCUSDT", "1h", specs, limit=40)
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    events = _parse_events(raw)
    metric_events = [data for event, data in events if event == "metric"]

    steps = [metric["payload"]["step"] for metric in metric_events]
    assert steps == ["data", "indicators", "levels", "patterns", "summary"]
    assert all(metric["payload"]["ms"] >= 0 for metric in metric_events)


@pytest.mark.anyio
async def test_stream_analysis_normalizes_symbol_in_events() -> None:
    """Tool events should expose the normalized ``BASE/QUOTE`` symbol."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 6)),
            "o": [float(v) for v in range(1, 6)],
            "h": [float(v) + 0.4 for v in range(1, 6)],
            "l": [float(v) - 0.4 for v in range(1, 6)],
            "c": [float(v) for v in range(1, 6)],
            "v": [100 + v for v in range(5)],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )

    iterator = await service.stream_analysis("btcusdt", "1h", [], limit=5)
    raw_events = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    parsed = _parse_events(raw_events)
    tool_events = [payload for event, payload in parsed if event == "tool_start"]
    assert tool_events, "Expected at least one tool_start event"
    tool_payload = tool_events[0]["payload"]
    assert tool_payload["symbol"] == "BTC/USDT"
