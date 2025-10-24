"""Routes exposing market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.market import MarketDataResponse, OhlcvQuery
from chart_mcp.services.data_providers.base import MarketDataProvider as DataProvider
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.data_adapter import normalize_ohlcv_frame
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_provider(request: Request) -> DataProvider:
    """Access the shared market data provider from app state."""
    return cast(DataProvider, request.app.state.provider)


@router.get("/ohlcv", response_model=MarketDataResponse)
def get_ohlcv(
    provider: Annotated[DataProvider, Depends(get_provider)],
    query: Annotated[OhlcvQuery, Depends()],
) -> MarketDataResponse:
    """Return normalized OHLCV data while enforcing strict query validation."""

    parse_timeframe(query.timeframe)
    if query.start is not None and query.end is not None and query.end <= query.start:
        raise BadRequest("Parameter 'end' must be greater than 'start'")

    frame = provider.get_ohlcv(
        query.symbol,
        query.timeframe,
        limit=query.limit,
        start=query.start,
        end=query.end,
    )
    rows = normalize_ohlcv_frame(frame)
    return MarketDataResponse(
        symbol=query.symbol,
        timeframe=query.timeframe,
        source=provider.client.id if hasattr(provider, "client") else "custom",
        rows=rows,
        fetched_at=datetime.utcnow(),
    )
