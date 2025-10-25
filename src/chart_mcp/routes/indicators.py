"""Routes for computing technical indicators."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.indicators import (
    IndicatorMeta,
    IndicatorRequest,
    IndicatorResponse,
    IndicatorValue,
)
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(
    prefix="/api/v1/indicators",
    tags=["indicators"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_services(request: Request) -> tuple[MarketDataProvider, IndicatorService]:
    """Return provider and indicator service from the application state."""
    return request.app.state.provider, request.app.state.indicator_service


@router.post("/compute", response_model=IndicatorResponse)
def compute_indicator(
    payload: IndicatorRequest,
    services: tuple[MarketDataProvider, IndicatorService] = Depends(get_services),
) -> IndicatorResponse:
    """Compute selected indicator and return the time series."""
    provider, service = services
    parse_timeframe(payload.timeframe)
    frame = provider.get_ohlcv(payload.symbol, payload.timeframe, limit=payload.limit)
    data = service.compute(frame, payload.indicator, payload.params)
    cleaned = data.dropna()
    ts_values = frame.loc[cleaned.index, "ts"].astype(int).tolist()
    records = cleaned.to_dict(orient="records")
    series = [
        IndicatorValue(
            ts=int(ts_value),
            values={str(k): float(v) for k, v in record.items()},
        )
        for ts_value, record in zip(ts_values, records, strict=True)
    ]
    normalized_symbol = normalize_symbol(payload.symbol)
    meta = IndicatorMeta(
        symbol=normalized_symbol,
        timeframe=payload.timeframe,
        indicator=payload.indicator,
        params={k: float(v) for k, v in payload.params.items()},
    )
    return IndicatorResponse(series=series, meta=meta)
