"""Streaming route for SSE analysis."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable
from typing import Annotated, Dict, List, cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.services.indicators import SUPPORTED_INDICATORS
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.logging import set_request_metadata
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/stream",
    tags=["stream"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_streaming_service(request: Request) -> StreamingService:
    """Retrieve the streaming service from application state."""
    return cast(StreamingService, request.app.state.streaming_service)


@router.get(
    "/analysis",
    summary="Stream the multi-step analysis as SSE",
    description=(
        "Diffuse en temps réel les étapes de l'analyse (données, indicateurs, niveaux, "
        "patrons) ainsi que le texte IA tokenisé."
    ),
    response_description="Flux Server-Sent Events ordonné.",
)
async def stream_analysis(
    request: Request,
    symbol: Annotated[str, Query(..., min_length=3, max_length=20)],
    timeframe: Annotated[str, Query(...)],
    indicators: Annotated[
        str | None,
        Query(
            description="Comma separated indicator specs (e.g. ema:21,rsi:14)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, description="Number of OHLCV rows requested for the stream."),
    ] = 500,
    include_levels: Annotated[bool, Query()] = True,
    include_patterns: Annotated[bool, Query()] = True,
    streaming: Annotated[bool, Query()] = True,
    max_levels: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            alias="max",
            description="Maximum number of support/resistance levels to include.",
        ),
    ] = 10,
) -> StreamingResponse:
    """Stream analysis events using Server-Sent Events."""
    parse_timeframe(timeframe)
    # Log the user intent early so failed validation still emits useful context.
    set_request_metadata(symbol=symbol, timeframe=timeframe)
    if not streaming:
        raise BadRequest("streaming must remain enabled for SSE analysis")

    indicator_specs: List[Dict[str, object]] = []
    if indicators:
        raw_items = [item.strip() for item in indicators.split(",") if item.strip()]
        if len(raw_items) > 10:
            raise BadRequest("A maximum of 10 indicators can be requested per stream")
        seen_signatures: set[tuple[str, tuple[tuple[str, float], ...]]] = set()
        for item in raw_items:
            name, params = _parse_indicator_spec(item)
            signature = (name, tuple(sorted(params.items())))
            if signature in seen_signatures:
                # Ignore duplicate indicators with identical parameterisation to
                # keep the streaming job bounded and avoid redundant work.
                continue
            seen_signatures.add(signature)
            indicator_specs.append({"name": name, "params": params})
    else:
        indicator_specs = [
            {"name": "ema", "params": {"window": 50.0}},
            {"name": "rsi", "params": {"window": 14.0}},
        ]

    streaming_service = get_streaming_service(request)
    if limit > 5000:
        raise BadRequest("limit must be less than or equal to 5000 for streaming analysis")
    iterator = await streaming_service.stream_analysis(
        symbol,
        timeframe,
        indicator_specs,
        limit=limit,
        include_levels=include_levels,
        include_patterns=include_patterns,
        max_levels=max_levels,
    )

    async def _cancellation_guard() -> AsyncIterator[str]:
        """Yield SSE chunks and ensure graceful shutdown on cancellation."""

        async def _close_iterator() -> None:
            """Terminate the underlying streaming job when the client disconnects."""
            closer = getattr(iterator, "aclose", None)
            if callable(closer):
                maybe_coro = closer()
                if inspect.isawaitable(maybe_coro):
                    await cast(Awaitable[object], maybe_coro)
            stopper = getattr(iterator, "stop", None)
            if callable(stopper):
                stop_result = stopper()
                if inspect.isawaitable(stop_result):
                    await cast(Awaitable[object], stop_result)

        try:
            async for chunk in iterator:
                if await request.is_disconnected():
                    await _close_iterator()
                    break
                yield chunk
        except asyncio.CancelledError:
            await _close_iterator()
            raise

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_cancellation_guard(), media_type="text/event-stream", headers=headers)


def _parse_indicator_spec(spec: str) -> tuple[str, Dict[str, float]]:
    """Parse and validate a raw indicator specification into a mapping.

    Examples
    --------
    "ema:21" -> ("ema", {"window": 21.0})
    "macd:fast=12;slow=26" -> ("macd", {"fast": 12.0, "slow": 26.0})
    "rsi" -> ("rsi", {})

    """
    cleaned_spec = spec.strip()
    if not cleaned_spec:
        raise BadRequest("Indicator specification cannot be empty")
    if ":" not in cleaned_spec:
        name_only = cleaned_spec.lower()
        if name_only not in SUPPORTED_INDICATORS:
            allowed = ", ".join(sorted(SUPPORTED_INDICATORS))
            raise BadRequest(f"Unsupported indicator '{cleaned_spec}'. Allowed: {allowed}")
        return name_only, {}

    name_part, params_part = cleaned_spec.split(":", maxsplit=1)
    name = name_part.strip().lower()
    if not name:
        raise BadRequest("Indicator name cannot be empty")
    if name not in SUPPORTED_INDICATORS:
        allowed = ", ".join(sorted(SUPPORTED_INDICATORS))
        raise BadRequest(f"Unsupported indicator '{name}'. Allowed: {allowed}")
    params: Dict[str, float] = {}
    if not params_part:
        return name, params

    for token in params_part.split(";"):
        cleaned = token.strip()
        if not cleaned:
            continue
        if "=" in cleaned:
            key, value = cleaned.split("=", maxsplit=1)
            try:
                key_name = key.strip().lower()
                value_clean = value.strip()
                params[key_name] = float(value_clean)
            except ValueError as exc:  # pragma: no cover - defensive branch
                raise BadRequest(f"Invalid indicator parameter value: '{value}'") from exc
        else:
            try:
                params["window"] = float(cleaned)
            except ValueError as exc:
                raise BadRequest(f"Invalid indicator parameter value: '{cleaned}'") from exc
    return name, params
