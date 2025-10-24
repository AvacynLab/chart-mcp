"""Routes exposing market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, cast

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_token
from chart_mcp.schemas.market import MarketDataResponse, OhlcvRow
from chart_mcp.services.data_providers.base import MarketDataProvider as DataProvider
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/api/v1/market", tags=["market"], dependencies=[Depends(require_token)])


def get_provider(request: Request) -> DataProvider:
    """Access the shared market data provider from app state."""
    return cast(DataProvider, request.app.state.provider)


@router.get("/ohlcv", response_model=MarketDataResponse)
def get_ohlcv(
    provider: Annotated[DataProvider, Depends(get_provider)],
    symbol: str = Query(..., min_length=3, max_length=20),
    timeframe: str = Query(...),
    limit: int = Query(500, ge=10, le=2000),
    start: int | None = Query(None),
    end: int | None = Query(None),
) -> MarketDataResponse:
    """Return OHLCV data as JSON payload."""
    parse_timeframe(timeframe)
    # Validate timeframe early to provide consistent error responses before hitting the provider.
    if start and end and end <= start:
        raise BadRequest("Parameter 'end' must be greater than 'start'")
    frame = provider.get_ohlcv(symbol, timeframe, limit=limit, start=start, end=end)
    rows: List[OhlcvRow] = [
        OhlcvRow(
            ts=int(row.ts),
            open=float(row.o),
            high=float(row.h),
            low=float(row.l),
            close=float(row.c),
            volume=float(row.v),
        )
        for row in frame.itertuples(index=False)
    ]
    return MarketDataResponse(
        symbol=symbol,
        timeframe=timeframe,
        source=provider.client.id if hasattr(provider, "client") else "custom",
        rows=rows,
        fetched_at=datetime.utcnow(),
    )
