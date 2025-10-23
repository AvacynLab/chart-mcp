"""Routes exposing market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_token
from chart_mcp.schemas.market import MarketDataResponse, OhlcvRow
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/api/v1/market", tags=["market"], dependencies=[Depends(require_token)])


def get_provider(request: Request) -> MarketDataProvider:
    """Retrieve provider stored on FastAPI application state."""

    return request.app.state.provider


@router.get("/ohlcv", response_model=MarketDataResponse)
def get_ohlcv(
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    limit: int = Query(500, ge=10, le=2000),
    start: int | None = Query(None),
    end: int | None = Query(None),
    provider: MarketDataProvider = Depends(get_provider),
) -> MarketDataResponse:
    """Return OHLCV data as JSON payload."""

    parse_timeframe(timeframe)
    if start and end and end <= start:
        raise BadRequest("Parameter 'end' must be greater than 'start'")
    frame = provider.get_ohlcv(symbol, timeframe, limit=limit, start=start, end=end)
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=int(row.ts), o=float(row.o), h=float(row.h), l=float(row.l), c=float(row.c), v=float(row.v))
        for row in frame.itertuples(index=False)
    ]
    return MarketDataResponse(
        symbol=symbol,
        timeframe=timeframe,
        source=provider.client.id if hasattr(provider, "client") else "custom",
        rows=rows,
        fetched_at=datetime.utcnow(),
    )
