"""Routes for computing technical indicators."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, Request

from chart_mcp.routes.auth import require_token
from chart_mcp.schemas.indicators import IndicatorRequest, IndicatorResponse, IndicatorValue
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.utils.timeframes import parse_timeframe

router = APIRouter(prefix="/api/v1/indicators", tags=["indicators"], dependencies=[Depends(require_token)])


def get_services(request: Request) -> tuple[MarketDataProvider, IndicatorService]:
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
    series = [
        IndicatorValue(ts=int(frame.iloc[idx]["ts"]), values={k: float(v) for k, v in row.items()})
        for idx, row in cleaned.iterrows()
    ]
    meta: Dict[str, float | str] = {
        "indicator": payload.indicator,
        **{k: float(v) for k, v in payload.params.items()},
    }
    return IndicatorResponse(series=series, meta=meta)
