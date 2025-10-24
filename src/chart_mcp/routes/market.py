"""Routes exposing market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, SupportsFloat, SupportsInt, cast

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
    rows: List[OhlcvRow] = []
    for ts, open_, high, low, close, volume in frame.itertuples(index=False, name=None):
        rows.append(
            OhlcvRow(
                ts=int(cast(SupportsInt, ts)),
                # Populate fields via their short aliases so the Pydantic signature aligns with NDJSON contract.
                o=float(cast(SupportsFloat, open_)),
                h=float(cast(SupportsFloat, high)),
                l=float(cast(SupportsFloat, low)),
                c=float(cast(SupportsFloat, close)),
                v=float(cast(SupportsFloat, volume)),
            )
        )
    return MarketDataResponse(
        symbol=symbol,
        timeframe=timeframe,
        source=provider.client.id if hasattr(provider, "client") else "custom",
        rows=rows,
        fetched_at=datetime.utcnow(),
    )
