"""Streaming orchestration service producing SSE events."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Dict, Iterable, List, Mapping, SupportsFloat, cast

from loguru import logger

from chart_mcp.schemas.streaming import (
    DoneDetails,
    DoneStreamPayload,
    ErrorDetails,
    ErrorStreamPayload,
    LevelDetail,
    LevelPreview,
    PatternDetail,
    ResultFinalDetails,
    ResultFinalStreamPayload,
    ResultPartialDetails,
    ResultPartialStreamPayload,
    TokenPayload,
    TokenStreamPayload,
    ToolEventDetails,
    ToolStreamPayload,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelCandidate, LevelsService
from chart_mcp.services.patterns import PatternResult, PatternsService
from chart_mcp.utils.errors import ApiError, BadRequest
from chart_mcp.utils.sse import SseStreamer


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
        limit: int = 500,
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

        """
        if limit <= 0 or limit > 5000:
            # Guardrail preventing callers from exhausting the provider by asking for
            # an unreasonable amount of historical data. The upper bound mirrors the
            # finance REST routes to keep behaviour consistent across surfaces.
            raise BadRequest("limit must be between 1 and 5000 for streaming analysis")
        streamer = SseStreamer()
        await streamer.start()

        async def _publish_metric(step: str, elapsed_seconds: float) -> None:
            """Emit a metric event capturing the time spent in a pipeline stage."""
            await streamer.publish(
                "metric",
                {
                    "type": "metric",
                    "payload": {
                        "step": step,
                        "ms": float(elapsed_seconds * 1000),
                    },
                },
            )

        async def _run_pipeline() -> None:
            """Execute the streaming pipeline while guarding against crashes."""
            try:
                await streamer.publish(
                    "tool_start",
                    ToolStreamPayload(
                        type="tool",
                        payload=ToolEventDetails(
                            tool="get_crypto_data",
                            symbol=symbol,
                            timeframe=timeframe,
                        ),
                    ).model_dump(),
                )
                start_data = time.perf_counter()
                frame = await asyncio.to_thread(
                    self.provider.get_ohlcv, symbol, timeframe, limit=limit
                )
                await _publish_metric("data", time.perf_counter() - start_data)
                await streamer.publish(
                    "tool_end",
                    ToolStreamPayload(
                        type="tool",
                        payload=ToolEventDetails(
                            tool="get_crypto_data",
                            rows=len(frame),
                        ),
                    ).model_dump(),
                )

                indicator_values: Dict[str, Dict[str, float]] = {}
                # Accumulate the latest indicator values to feed heuristics and streaming payloads.
                start_indicators = time.perf_counter()
                for spec in indicators:
                    name = str(spec.get("name") or "unknown")
                    params_raw = spec.get("params") or {}
                    params_mapping: Mapping[str, object] = (
                        params_raw if isinstance(params_raw, Mapping) else {}
                    )
                    params = {
                        str(k): float(cast(SupportsFloat, v)) for k, v in params_mapping.items()
                    }
                    data = await asyncio.to_thread(
                        self.indicator_service.compute, frame, name, params
                    )
                    cleaned = data.dropna()
                    latest = cleaned.iloc[-1].to_dict() if not cleaned.empty else {}
                    indicator_values[name] = {
                        k: float(cast(SupportsFloat, v)) for k, v in latest.items()
                    }
                    await streamer.publish(
                        "tool_end",
                        ToolStreamPayload(
                            type="tool",
                            payload=ToolEventDetails(
                                tool="compute_indicator",
                                name=name,
                                latest=indicator_values[name],
                            ),
                        ).model_dump(),
                    )
                await _publish_metric("indicators", time.perf_counter() - start_indicators)

                start_levels = time.perf_counter()
                levels: List[LevelCandidate] = await asyncio.to_thread(
                    self.levels_service.detect_levels, frame
                )
                await _publish_metric("levels", time.perf_counter() - start_levels)

                start_patterns = time.perf_counter()
                patterns: List[PatternResult] = await asyncio.to_thread(
                    self.patterns_service.detect, frame
                )
                await _publish_metric("patterns", time.perf_counter() - start_patterns)
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
                                )
                                for lvl in levels[:3]
                            ],
                        ),
                    ).model_dump(),
                )

                start_summary = time.perf_counter()
                summary = await asyncio.to_thread(
                    self.analysis_service.summarize,
                    symbol,
                    timeframe,
                    {
                        name: float(cast(SupportsFloat, next(iter(values.values()), 0.0)))
                        for name, values in indicator_values.items()
                    },
                    levels,
                    patterns,
                )
                await _publish_metric("summary", time.perf_counter() - start_summary)
                for sentence in summary.split("."):
                    text = sentence.strip()
                    if text:
                        await streamer.publish(
                            "token",
                            TokenStreamPayload(
                                type="token",
                                payload=TokenPayload(text=f"{text}."),
                            ).model_dump(),
                        )
                await streamer.publish(
                    "result_final",
                    ResultFinalStreamPayload(
                        type="result_final",
                        payload=ResultFinalDetails(
                            summary=summary,
                            levels=[
                                LevelDetail(
                                    price=float(lvl.price),
                                    kind=lvl.kind,
                                    strength=float(lvl.strength),
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
                        payload=DoneDetails(status="success"),
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

        asyncio.create_task(_run_pipeline())
        async for chunk in streamer.stream():
            yield chunk
