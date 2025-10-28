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


def _build_candidate(
    kind: str,
    price: float,
    timestamps: list[int],
    *,
    window_start: int,
    window_end: int,
    merge_threshold: float = 0.0025,
) -> LevelCandidate:
    """Construct a :class:`LevelCandidate` with repeated touches."""
    candidate = LevelCandidate(
        kind=kind, window_start=window_start, window_end=window_end, merge_threshold=merge_threshold
    )
    for idx, ts in enumerate(timestamps):
        candidate.add_touch(price, ts, idx)
    return candidate


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

    def detect_levels(  # type: ignore[override]
        self,
        frame: pd.DataFrame,
        *,
        max_levels: int = 10,
        distance: int | None = None,
        prominence: float | None = None,
        merge_threshold: float = 0.0025,
        min_touches: int = 2,
    ) -> list[LevelCandidate]:
        return []


class _RecordingLevels(LevelsService):
    """Levels stub capturing the requested ``max_levels`` for assertions."""

    def __init__(self, levels: list[LevelCandidate]) -> None:
        self._levels = levels
        self.last_max_levels: Optional[int] = None

    def detect_levels(  # type: ignore[override]
        self,
        frame: pd.DataFrame,
        *,
        max_levels: int = 10,
        distance: int | None = None,
        prominence: float | None = None,
        merge_threshold: float = 0.0025,
        min_touches: int = 2,
    ) -> list[LevelCandidate]:
        self.last_max_levels = max_levels
        ranked = sorted(self._levels, key=lambda lvl: lvl.strength, reverse=True)
        # Return a copy so callers can mutate the result without affecting the fixture.
        return list(ranked[:max_levels])


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
    assert steps == ["ohlcv", "indicators", "levels", "patterns", "summary"]
    assert all(metric["payload"]["ms"] >= 0 for metric in metric_events)


@pytest.mark.anyio
async def test_stream_analysis_normalizes_symbol_in_events() -> None:
    """Stage metadata should expose the normalized ``BASE/QUOTE`` symbol."""
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
    step_events = [payload for event, payload in parsed if event == "step:start"]
    assert step_events, "Expected at least one step:start event"
    ohlcv_event = next(
        payload for payload in step_events if payload["payload"]["stage"] == "ohlcv"
    )
    metadata = ohlcv_event["payload"].get("metadata", {})
    assert metadata["symbol"] == "BTC/USDT"


@pytest.mark.anyio
async def test_stream_analysis_partial_event_exposes_progress_ratio() -> None:
    """Partial payloads expose a bounded progress ratio for UI loaders."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 16)),
            "o": [float(v) for v in range(1, 16)],
            "h": [float(v) + 0.6 for v in range(1, 16)],
            "l": [float(v) - 0.6 for v in range(1, 16)],
            "c": [float(v) for v in range(1, 16)],
            "v": [200 + v for v in range(15)],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )

    iterator = await service.stream_analysis(
        "BTCUSDT",
        "4h",
        [{"name": "ema", "params": {"window": 5}}],
        limit=15,
        include_levels=True,
        include_patterns=False,
    )
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    events = _parse_events(raw)
    partial_payloads = [payload for event, payload in events if event == "result_partial"]
    assert partial_payloads, "Expected a partial event in the SSE stream"
    progress = partial_payloads[0]["payload"].get("progress")
    assert progress is not None
    assert 0.0 < progress < 1.0
    steps = partial_payloads[0]["payload"].get("steps")
    assert isinstance(steps, list) and steps, "Progress steps should be provided"
    status_map = {step["name"]: step["status"] for step in steps}
    progress_map = {step["name"]: step.get("progress") for step in steps}
    assert status_map["ohlcv"] == "completed"
    assert status_map["indicators"] == "completed"
    assert status_map["levels"] == "completed"
    assert status_map["patterns"] == "skipped"
    assert status_map["summary"] == "pending"
    assert progress_map["ohlcv"] == pytest.approx(1.0)
    assert progress_map["indicators"] == pytest.approx(1.0)
    assert progress_map["levels"] == pytest.approx(1.0)
    assert progress_map["patterns"] == pytest.approx(1.0)
    assert progress_map["summary"] == pytest.approx(0.0)


@pytest.mark.anyio
async def test_stream_analysis_progress_handles_skipped_stages() -> None:
    """When optional stages are skipped they are labelled and ignored in ratios."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 12)),
            "o": [float(v) for v in range(1, 12)],
            "h": [float(v) + 0.4 for v in range(1, 12)],
            "l": [float(v) - 0.4 for v in range(1, 12)],
            "c": [float(v) for v in range(1, 12)],
            "v": [150 + v for v in range(11)],
        }
    )
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        _DummyLevels(),
        _DummyPatterns(),
        _DummyLLM(),
    )

    iterator = await service.stream_analysis(
        "ETHUSDT",
        "1h",
        [],
        limit=11,
        include_levels=False,
        include_patterns=False,
    )
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    events = _parse_events(raw)
    partial_payloads = [payload for event, payload in events if event == "result_partial"]
    assert partial_payloads, "Expected a partial payload when streaming"
    payload = partial_payloads[0]["payload"]
    assert payload["progress"] == pytest.approx(2.0 / 3.0, rel=1e-6)
    step_payload = {step["name"]: step for step in payload.get("steps", [])}
    assert step_payload["levels"]["status"] == "skipped"
    assert step_payload["patterns"]["status"] == "skipped"
    assert step_payload["summary"]["status"] == "pending"
    assert step_payload["levels"]["progress"] == pytest.approx(1.0)
    assert step_payload["patterns"]["progress"] == pytest.approx(1.0)
    assert step_payload["summary"]["progress"] == pytest.approx(0.0)


@pytest.mark.anyio
async def test_stream_analysis_honours_max_levels_limit() -> None:
    """The streaming pipeline should enforce the caller-provided max_levels bound."""
    frame = pd.DataFrame(
        {
            "ts": list(range(1, 61)),
            "o": [float(v) for v in range(1, 61)],
            "h": [float(v) + 0.4 for v in range(1, 61)],
            "l": [float(v) - 0.4 for v in range(1, 61)],
            "c": [float(v) for v in range(1, 61)],
            "v": [200 + v for v in range(60)],
        }
    )
    levels_fixture = [
        _build_candidate(
            kind="resistance",
            price=102.5,
            timestamps=list(range(1, 8)),
            window_start=1,
            window_end=60,
        ),
        _build_candidate(
            kind="support",
            price=95.0,
            timestamps=list(range(10, 15)),
            window_start=1,
            window_end=60,
        ),
        _build_candidate(
            kind="resistance",
            price=108.0,
            timestamps=list(range(20, 23)),
            window_start=1,
            window_end=60,
        ),
    ]
    levels_service = _RecordingLevels(levels_fixture)
    service = StreamingService(
        _StaticProvider(frame),
        IndicatorService(),
        levels_service,
        _DummyPatterns(),
        _DummyLLM(),
    )

    iterator = await service.stream_analysis(
        "BTCUSDT",
        "1h",
        [],
        limit=50,
        max_levels=2,
    )
    raw = await asyncio.wait_for(_collect_events(iterator), timeout=1.0)
    await iterator.aclose()

    events = _parse_events(raw)
    partial_payload = next(data for event, data in events if event == "result_partial")
    final_payload = next(data for event, data in events if event == "result_final")

    partial_levels = partial_payload["payload"].get("levels", [])
    final_levels = final_payload["payload"].get("levels", [])

    assert len(partial_levels) == 2
    assert len(final_levels) == 2
    assert levels_service.last_max_levels == 2

    partial_strengths = [level["strength"] for level in partial_levels]
    final_strengths = [level["strength"] for level in final_levels]

    assert partial_strengths == sorted(partial_strengths, reverse=True)
    assert final_strengths == sorted(final_strengths, reverse=True)
