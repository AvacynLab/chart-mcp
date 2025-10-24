"""Streaming orchestration service producing SSE events."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, Iterable, List, Mapping, SupportsFloat, cast

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelCandidate, LevelsService
from chart_mcp.services.patterns import PatternResult, PatternsService
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
        """Stream SSE chunks by chaining provider, indicator, and LLM calls."""
        streamer = SseStreamer()
        await streamer.start()

        async def _run_pipeline() -> None:
            await streamer.publish(
                "tool_start",
                {
                    "type": "tool",
                    "payload": {
                        "tool": "get_crypto_data",
                        "symbol": symbol,
                        "timeframe": timeframe,
                    },
                },
            )
            frame = await asyncio.to_thread(self.provider.get_ohlcv, symbol, timeframe, limit=limit)
            await streamer.publish(
                "tool_end",
                {"type": "tool", "payload": {"tool": "get_crypto_data", "rows": len(frame)}},
            )

            indicator_values: Dict[str, Dict[str, float]] = {}
            # Accumulate the latest indicator values to feed heuristics and streaming payloads.
            for spec in indicators:
                name = str(spec.get("name") or "unknown")
                params_raw = spec.get("params") or {}
                params_mapping: Mapping[str, object] = (
                    params_raw if isinstance(params_raw, Mapping) else {}
                )
                params = {
                    str(k): float(cast(SupportsFloat, v))
                    for k, v in params_mapping.items()
                }
                data = await asyncio.to_thread(self.indicator_service.compute, frame, name, params)
                cleaned = data.dropna()
                latest = cleaned.iloc[-1].to_dict() if not cleaned.empty else {}
                indicator_values[name] = {
                    k: float(cast(SupportsFloat, v)) for k, v in latest.items()
                }
                await streamer.publish(
                    "tool_end",
                    {
                        "type": "tool",
                        "payload": {
                            "tool": "compute_indicator",
                            "name": name,
                            "latest": indicator_values[name],
                        },
                    },
                )

            levels: List[LevelCandidate] = await asyncio.to_thread(
                self.levels_service.detect_levels, frame
            )
            patterns: List[PatternResult] = await asyncio.to_thread(
                self.patterns_service.detect, frame
            )
            await streamer.publish(
                "result_partial",
                {
                    "type": "result_partial",
                    "payload": {
                        "indicators": indicator_values,
                        "levels": [
                            {"price": lvl.price, "kind": lvl.kind, "strength": lvl.strength}
                            for lvl in levels[:3]
                        ],
                    },
                },
            )

            summary = await asyncio.to_thread(
                self.analysis_service.summarize,
                symbol,
                timeframe,
                {
                    name: float(
                        cast(SupportsFloat, next(iter(values.values()), 0.0))
                    )
                    for name, values in indicator_values.items()
                },
                levels,
                patterns,
            )
            for sentence in summary.split("."):
                text = sentence.strip()
                if text:
                    await streamer.publish(
                        "token", {"type": "token", "payload": {"text": text + "."}}
                    )
            await streamer.publish(
                "result_final",
                {
                    "type": "result_final",
                    "payload": {
                        "summary": summary,
                        "levels": [
                            {
                                "price": lvl.price,
                                "kind": lvl.kind,
                                "strength": lvl.strength,
                                "ts_range": lvl.ts_range,
                            }
                            for lvl in levels
                        ],
                        "patterns": [
                            {
                                "name": p.name,
                                "score": p.score,
                                "confidence": p.confidence,
                                "start_ts": p.start_ts,
                                "end_ts": p.end_ts,
                            }
                            for p in patterns
                        ],
                    },
                },
            )
            await streamer.publish("done", {"type": "done", "payload": {}})
            await streamer.stop()

        asyncio.create_task(_run_pipeline())
        async for chunk in streamer.stream():
            yield chunk
