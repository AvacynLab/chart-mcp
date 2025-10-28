"""Routes exposing market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.market import MarketDataResponse, OhlcvQuery
from chart_mcp.services.data_providers.base import MarketDataProvider as DataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.utils.data_adapter import normalize_ohlcv_frame
from chart_mcp.utils.errors import BadRequest
from chart_mcp.utils.logging import set_request_metadata
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_provider(request: Request) -> DataProvider:
    """Access the shared market data provider from app state."""
    return cast(DataProvider, request.app.state.provider)


@router.get(
    "/ohlcv",
    response_model=MarketDataResponse,
    summary="Retrieve normalized OHLCV candles",
    description=(
        "Retourne les chandeliers OHLCV normalisés pour un symbole donné en "
        "validant strictement la période demandée."
    ),
    response_description="Série OHLCV normalisée triée par timestamp croissant.",
)
def get_ohlcv(
    provider: Annotated[DataProvider, Depends(get_provider)],
    query: Annotated[OhlcvQuery, Depends()],
) -> MarketDataResponse:
    """Return normalized OHLCV data while enforcing strict query validation."""
    parse_timeframe(query.timeframe)
    start = query.resolved_start()
    end = query.resolved_end()
    if start is not None and end is not None and end <= start:
        raise BadRequest("Parameter 'end' must be greater than 'start'")

    frame = provider.get_ohlcv(
        query.symbol,
        query.timeframe,
        limit=query.limit,
        start=start,
        end=end,
    )
    rows = normalize_ohlcv_frame(frame)
    normalized_symbol = normalize_symbol(query.symbol)
    # Enrich the structured logging context so the middleware exposes
    # ``symbol``/``timeframe`` even for pure REST requests.
    set_request_metadata(symbol=normalized_symbol, timeframe=query.timeframe)
    return MarketDataResponse(
        symbol=normalized_symbol,
        timeframe=query.timeframe,
        source=provider.client.id if hasattr(provider, "client") else "custom",
        rows=rows,
        fetched_at=datetime.utcnow(),
    )
