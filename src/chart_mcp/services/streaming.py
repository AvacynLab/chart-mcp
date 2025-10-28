"""Streaming orchestration service producing SSE events."""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Dict, Iterable, List, Mapping, SupportsFloat, cast

from loguru import logger

from chart_mcp.schemas.streaming import (
    DoneDetails,
    DoneStreamPayload,
    ErrorDetails,
    ErrorStreamPayload,
    LevelDetail,
    LevelPreview,
    MetricDetails,
    MetricStreamPayload,
    PatternDetail,
    ProgressStep,
    ResultFinalDetails,
    ResultFinalStreamPayload,
    ResultPartialDetails,
    ResultPartialStreamPayload,
    StepEndStreamPayload,
    StepEventDetails,
    StepStartStreamPayload,
    TokenPayload,
    TokenStreamPayload,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService, AnalysisSummary
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelCandidate, LevelsService
from chart_mcp.services.metrics import metrics
from chart_mcp.services.patterns import PatternResult, PatternsService
from chart_mcp.utils.errors import ApiError, BadRequest
from chart_mcp.utils.logging import log_stage, set_request_metadata
from chart_mcp.utils.sse import SseStreamer


class _StageStatus(str, Enum):
    """Enumeration of pipeline stage states for structured progress output."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class _StageProgress:
    """Track the completion metadata for an individual pipeline stage."""

    name: str
    weight: float = 1.0
    status: _StageStatus = _StageStatus.PENDING
    progress: float = 0.0

    def mark_in_progress(self) -> None:
        """Record that the stage is currently executing."""
        self.status = _StageStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        """Record that the stage has finished successfully."""
        self.set_progress(1.0)
        self.status = _StageStatus.COMPLETED

    def skip(self) -> None:
        """Mark a stage as skipped while excluding it from progress weighting."""
        self.status = _StageStatus.SKIPPED
        self.weight = 0.0
        self.progress = 1.0

    def set_progress(self, ratio: float) -> None:
        """Update the fractional completion for the stage (monotonic clamp)."""
        clamped = min(max(ratio, 0.0), 1.0)
        if clamped < self.progress:
            return
        self.progress = clamped


class StreamingService:
    """Coordinate services to emit analysis events progressively."""

    def __init__(
        self,
        provider: MarketDataProvider,
        indicator_service: IndicatorService,
        levels_service: LevelsService,
        patterns_service: PatternsService,
        analysis_service: AnalysisLLMService,
    ) -> None:
        self.provider = provider
        self.indicator_service = indicator_service
        self.levels_service = levels_service
        self.patterns_service = patterns_service
        self.analysis_service = analysis_service

    async def stream_analysis(
        self,
        symbol: str,
        timeframe: str,
        indicators: Iterable[Dict[str, object]],
        *,
        limit: int = 500,
        include_levels: bool = True,
        include_patterns: bool = True,
        streaming: bool = True,
        max_levels: int = 10,
    ) -> AsyncIterator[str]:
        """Stream SSE chunks by chaining provider, indicator, and LLM calls.

        Parameters
        ----------
        symbol:
            Trading pair requested by the caller.
        timeframe:
            Candlestick timeframe (validated upstream).
        indicators:
            Sequence describing the technical indicators that should be computed.
        limit:
            Number of OHLCV rows requested from the provider. Guarded to keep the
            streaming job bounded and deterministic across environments.
        include_levels:
            Toggle indicating whether support/resistance detection should run.
        include_patterns:
            Toggle indicating whether chart pattern detection should run.
        streaming:
            Flag kept for parity with the REST query parameters. Only ``True`` is
            currently supported; a ``False`` value results in a :class:`BadRequest`.
        max_levels:
            Upper bound on the number of levels returned in the partial and final
            payloads. Mirrors the REST endpoint so UI components can request a
            consistent amount of data across surfaces.

        """
        if limit <= 0 or limit > 5000:
            # Guardrail preventing callers from exhausting the provider by asking for
            # an unreasonable amount of historical data. The upper bound mirrors the
            # finance REST routes to keep behaviour consistent across surfaces.
            raise BadRequest("limit must be between 1 and 5000 for streaming analysis")
        if not streaming:
            raise BadRequest("streaming mode must remain enabled")
        if max_levels <= 0 or max_levels > 100:
            raise BadRequest("max_levels must be between 1 and 100")
        normalized_symbol = normalize_symbol(symbol)
        # Normalizing the symbol keeps SSE payloads aligned with the REST
        # responses (`BTC/USDT`) and allows downstream services to reuse cached
        # results across surfaces. The metadata enrichment ensures the logging
        # middleware emits structured fields (symbol/timeframe) even for long
        # running SSE streams.
        set_request_metadata(symbol=normalized_symbol, timeframe=timeframe)
        streamer = SseStreamer()
        await streamer.start()

        async def _publish_metric(step: str, elapsed_seconds: float) -> None:
            """Emit a metric event capturing the time spent in a pipeline stage."""
            metrics.observe_stage_duration(step, elapsed_seconds)
            await streamer.publish(
                "metric",
                MetricStreamPayload(
                    type="metric",
                    payload=MetricDetails(step=step, ms=float(elapsed_seconds * 1000)),
                ).model_dump(),
            )

        indicator_specs = list(indicators)
        # Copying the iterable allows the service to iterate multiple times (for
        # progress calculation and introspection) without consuming a generator
        # passed by the caller.

        stages: Dict[str, _StageProgress] = {
            "ohlcv": _StageProgress("ohlcv"),
            "indicators": _StageProgress("indicators"),
            "levels": _StageProgress("levels"),
            "patterns": _StageProgress("patterns"),
            "summary": _StageProgress("summary"),
        }
        if not include_levels:
            stages["levels"].skip()
        if not include_patterns:
            stages["patterns"].skip()

        def _progress_snapshot() -> tuple[float, List[ProgressStep]]:
            """Compute the cumulative progress ratio and stage status list."""
            total_weight = sum(stage.weight for stage in stages.values() if stage.weight > 0.0)
            if total_weight <= 0:
                ratio = 0.0
            else:
                # Multiply each stage weight by its fractional completion to obtain a
                # smooth ratio in [0, 1]. Skipped stages expose ``weight = 0`` so they
                # are ignored in the computation.
                accumulated = sum(stage.weight * stage.progress for stage in stages.values())
                ratio = min(max(accumulated / total_weight, 0.0), 1.0)
            step_snapshots = [
                ProgressStep(name=stage.name, status=stage.status.value, progress=stage.progress)
                for stage in stages.values()
            ]
            return ratio, step_snapshots

        async def _run_pipeline() -> None:
            """Execute the streaming pipeline while guarding against crashes."""
            try:
                with log_stage("ohlcv"):
                    await streamer.publish(
                        "step:start",
                        StepStartStreamPayload(
                            type="step:start",
                            payload=StepEventDetails(
                                stage="ohlcv",
                                description="Fetching historical OHLCV candles",
                                metadata={
                                    "symbol": normalized_symbol,
                                    "timeframe": timeframe,
                                    "limit": limit,
                                },
                            ),
                        ).model_dump(),
                    )
                    stages["ohlcv"].mark_in_progress()
                    start_data = time.perf_counter()
                    frame = await asyncio.to_thread(
                        self.provider.get_ohlcv, normalized_symbol, timeframe, limit=limit
                    )
                    stages["ohlcv"].mark_completed()
                    elapsed_data = time.perf_counter() - start_data
                    await _publish_metric("ohlcv", elapsed_data)
                    await streamer.publish(
                        "step:end",
                        StepEndStreamPayload(
                            type="step:end",
                            payload=StepEventDetails(
                                stage="ohlcv",
                                elapsed_ms=float(elapsed_data * 1000),
                                metadata={"rows": len(frame)},
                            ),
                        ).model_dump(),
                    )

                indicator_values: Dict[str, Dict[str, float]] = {}
                # Accumulate the latest indicator values to feed heuristics and streaming payloads.
                with log_stage("indicators"):
                    await streamer.publish(
                        "step:start",
                        StepStartStreamPayload(
                            type="step:start",
                            payload=StepEventDetails(
                                stage="indicators",
                                description="Computing requested indicators",
                                metadata={"requested": len(indicator_specs)},
                            ),
                        ).model_dump(),
                    )
                    stages["indicators"].mark_in_progress()
                    start_indicators = time.perf_counter()
                    total_specs = max(len(indicator_specs), 1)
                    for index, spec in enumerate(indicator_specs, start=1):
                        name = str(spec.get("name") or "unknown")
                        params_raw = spec.get("params") or {}
                        params_mapping: Mapping[str, object] = (
                            params_raw if isinstance(params_raw, Mapping) else {}
                        )
                        params = {
                            str(k): float(cast(SupportsFloat, v))
                            for k, v in params_mapping.items()
                        }
                        data = await asyncio.to_thread(
                            self.indicator_service.compute, frame, name, params
                        )
                        cleaned = data.dropna()
                        latest = cleaned.iloc[-1].to_dict() if not cleaned.empty else {}
                        indicator_values[name] = {
                            k: float(cast(SupportsFloat, v)) for k, v in latest.items()
                        }
                        # Reflect incremental indicator progress so the ratio evolves smoothly.
                        stages["indicators"].set_progress(index / total_specs)
                    stages["indicators"].mark_completed()
                    elapsed_indicators = time.perf_counter() - start_indicators
                    await _publish_metric("indicators", elapsed_indicators)
                    await streamer.publish(
                        "step:end",
                        StepEndStreamPayload(
                            type="step:end",
                            payload=StepEventDetails(
                                stage="indicators",
                                elapsed_ms=float(elapsed_indicators * 1000),
                                metadata={"computed": len(indicator_values)},
                            ),
                        ).model_dump(),
                    )

                levels: List[LevelCandidate] = []
                if include_levels:
                    with log_stage("levels"):
                        await streamer.publish(
                            "step:start",
                            StepStartStreamPayload(
                                type="step:start",
                                payload=StepEventDetails(
                                    stage="levels",
                                    description="Detecting support and resistance zones",
                                    metadata={"max_levels": max_levels},
                                ),
                            ).model_dump(),
                        )
                        stages["levels"].mark_in_progress()
                        start_levels = time.perf_counter()
                        levels = await asyncio.to_thread(
                            self.levels_service.detect_levels, frame, max_levels=max_levels
                        )
                        elapsed_levels = time.perf_counter() - start_levels
                        await _publish_metric("levels", elapsed_levels)
                        stages["levels"].mark_completed()
                        await streamer.publish(
                            "step:end",
                            StepEndStreamPayload(
                                type="step:end",
                                payload=StepEventDetails(
                                    stage="levels",
                                    elapsed_ms=float(elapsed_levels * 1000),
                                    metadata={"detected": len(levels)},
                                ),
                            ).model_dump(),
                        )
                else:
                    await _publish_metric("levels", 0.0)
                    await streamer.publish(
                        "step:start",
                        StepStartStreamPayload(
                            type="step:start",
                            payload=StepEventDetails(
                                stage="levels",
                                description="Level detection skipped by caller",
                                metadata={"skipped": True},
                            ),
                        ).model_dump(),
                    )
                    await streamer.publish(
                        "step:end",
                        StepEndStreamPayload(
                            type="step:end",
                            payload=StepEventDetails(
                                stage="levels",
                                elapsed_ms=0.0,
                                metadata={"skipped": True},
                            ),
                        ).model_dump(),
                    )

                patterns: List[PatternResult] = []
                if include_patterns:
                    with log_stage("patterns"):
                        await streamer.publish(
                            "step:start",
                            StepStartStreamPayload(
                                type="step:start",
                                payload=StepEventDetails(
                                    stage="patterns",
                                    description="Detecting chart patterns",
                                ),
                            ).model_dump(),
                        )
                        stages["patterns"].mark_in_progress()
                        start_patterns = time.perf_counter()
                        patterns = await asyncio.to_thread(self.patterns_service.detect, frame)
                        elapsed_patterns = time.perf_counter() - start_patterns
                        await _publish_metric("patterns", elapsed_patterns)
                        stages["patterns"].mark_completed()
                        await streamer.publish(
                            "step:end",
                            StepEndStreamPayload(
                                type="step:end",
                                payload=StepEventDetails(
                                    stage="patterns",
                                    elapsed_ms=float(elapsed_patterns * 1000),
                                    metadata={"detected": len(patterns)},
                                ),
                            ).model_dump(),
                        )
                else:
                    await _publish_metric("patterns", 0.0)
                    await streamer.publish(
                        "step:start",
                        StepStartStreamPayload(
                            type="step:start",
                            payload=StepEventDetails(
                                stage="patterns",
                                description="Pattern detection skipped by caller",
                                metadata={"skipped": True},
                            ),
                        ).model_dump(),
                    )
                    await streamer.publish(
                        "step:end",
                        StepEndStreamPayload(
                            type="step:end",
                            payload=StepEventDetails(
                                stage="patterns",
                                elapsed_ms=0.0,
                                metadata={"skipped": True},
                            ),
                        ).model_dump(),
                    )
                progress, step_snapshots = _progress_snapshot()
                await streamer.publish(
                    "result_partial",
                    ResultPartialStreamPayload(
                        type="result_partial",
                        payload=ResultPartialDetails(
                            indicators=indicator_values,
                            levels=[
                                LevelPreview(
                                    price=float(lvl.price),
                                    kind=lvl.kind,
                                    strength=float(lvl.strength),
                                    label=lvl.strength_label,
                                )
                                for lvl in levels[: min(3, max_levels)]
                            ],
                            progress=progress,
                            steps=step_snapshots,
                        ),
                    ).model_dump(),
                )

                with log_stage("summary"):
                    await streamer.publish(
                        "step:start",
                        StepStartStreamPayload(
                            type="step:start",
                            payload=StepEventDetails(
                                stage="summary",
                                description="Generating pedagogical AI summary",
                            ),
                        ).model_dump(),
                    )
                    stages["summary"].mark_in_progress()
                    start_summary = time.perf_counter()
                    summary_generator = self.analysis_service.stream_summary(
                        normalized_symbol,
                        timeframe,
                        {
                            name: float(cast(SupportsFloat, next(iter(values.values()), 0.0)))
                            for name, values in indicator_values.items()
                        },
                        levels,
                        patterns,
                    )
                    analysis_output: AnalysisSummary | None = None
                    try:
                        while True:
                            token = next(summary_generator)
                            await streamer.publish(
                                "token",
                                TokenStreamPayload(
                                    type="token",
                                    payload=TokenPayload(text=token),
                                ).model_dump(),
                            )
                    except StopIteration as stop:
                        analysis_output = stop.value
                    elapsed_summary = time.perf_counter() - start_summary
                    await _publish_metric("summary", elapsed_summary)
                    stages["summary"].mark_completed()
                    if analysis_output is None:  # pragma: no cover - defensive branch
                        raise RuntimeError("LLM summary generation did not return a result")
                    summary_text = analysis_output.summary
                    await streamer.publish(
                        "step:end",
                        StepEndStreamPayload(
                            type="step:end",
                            payload=StepEventDetails(
                                stage="summary",
                                elapsed_ms=float(elapsed_summary * 1000),
                                metadata={"tokens": len(summary_text.split())},
                            ),
                        ).model_dump(),
                    )
                    await streamer.publish(
                        "result_final",
                        ResultFinalStreamPayload(
                            type="result_final",
                            payload=ResultFinalDetails(
                                summary=summary_text,
                                levels=[
                                    LevelDetail(
                                        price=float(lvl.price),
                                        kind=lvl.kind,
                                        strength=float(lvl.strength),
                                        label=lvl.strength_label,
                                        ts_range=(int(lvl.ts_range[0]), int(lvl.ts_range[1])),
                                    )
                                    for lvl in levels
                                ],
                                patterns=[
                                    PatternDetail(
                                        name=p.name,
                                        score=float(p.score),
                                        confidence=float(p.confidence),
                                        start_ts=int(p.start_ts),
                                        end_ts=int(p.end_ts),
                                    )
                                    for p in patterns
                                ],
                            ),
                        ).model_dump(),
                    )
                    await streamer.publish(
                        "done",
                        DoneStreamPayload(
                            type="done",
                            payload=DoneDetails(status="ok"),
                        ).model_dump(),
                    )
            except ApiError as exc:
                # Surface domain validation issues to the client without terminating the stream abruptly.
                logger.warning(
                    "streaming.pipeline_api_error",
                    error_code=exc.code,
                    message=exc.message,
                )
                await streamer.publish(
                    "error",
                    ErrorStreamPayload(
                        type="error",
                        payload=ErrorDetails(code=exc.code, message=exc.message),
                    ).model_dump(),
                )
                await streamer.publish(
                    "done",
                    DoneStreamPayload(
                        type="done",
                        payload=DoneDetails(status="error", code=exc.code),
                    ).model_dump(),
                )
            except Exception:
                # Log unexpected crashes with a traceback while emitting a generic error message.
                logger.exception("streaming.pipeline_unhandled")
                await streamer.publish(
                    "error",
                    ErrorStreamPayload(
                        type="error",
                        payload=ErrorDetails(
                            code="internal_error",
                            message="Streaming pipeline failed",
                        ),
                    ).model_dump(),
                )
                await streamer.publish(
                    "done",
                    DoneStreamPayload(
                        type="done",
                        payload=DoneDetails(status="error", code="internal_error"),
                    ).model_dump(),
                )
            finally:
                await streamer.stop()

        pipeline_task = asyncio.create_task(_run_pipeline())

        class _StreamingJob(AsyncIterator[str]):
            """Async iterator coordinating stream consumption and cleanup."""

            def __init__(self) -> None:
                self._stream = streamer.stream()
                self._terminated = False

            def __aiter__(self) -> _StreamingJob:
                return self

            async def __anext__(self) -> str:
                try:
                    return await self._stream.__anext__()
                except StopAsyncIteration:
                    self._terminated = True
                    raise

            async def aclose(self) -> None:
                if self._terminated:
                    return
                self._terminated = True
                await self._shutdown()

            async def stop(self) -> None:
                if self._terminated:
                    return
                self._terminated = True
                await self._shutdown()

            async def _shutdown(self) -> None:
                if not pipeline_task.done():
                    pipeline_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await pipeline_task
                await streamer.stop()

        job = _StreamingJob()
        return cast(AsyncIterator[str], job)
