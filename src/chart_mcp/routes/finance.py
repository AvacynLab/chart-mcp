"""Routes providing finance-specific utilities (backtests, etc.)."""

from __future__ import annotations

import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request

from chart_mcp.routes.auth import require_regular_user, require_token
from chart_mcp.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    EquityPoint,
    MetricsModel,
    TradeModel,
)
from chart_mcp.schemas.finance import (
    ChartArtifactQuery,
    ChartArtifactResponse,
    ChartCandleDetails,
    ChartOverlayToggle,
    ChartRangeModel,
    FundamentalsQuery,
    FundamentalsResponse,
    NewsItemModel,
    NewsQuery,
    NewsResponse,
    OverlayPointModel,
    OverlaySeriesModel,
    QuoteQuery,
    QuoteResponse,
    ScreenedAssetModel,
    ScreenQuery,
    ScreenResponse,
)
from chart_mcp.services.backtest import BacktestResult, BacktestService
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.finance import (
    ChartCandleSnapshot,
    FinanceDataService,
    OverlayRequest,
)
from chart_mcp.utils.data_adapter import normalize_ohlcv_frame
from chart_mcp.utils.errors import BadRequest

router = APIRouter(
    prefix="/api/v1/finance",
    tags=["finance"],
    dependencies=[Depends(require_token), Depends(require_regular_user)],
)


def get_provider(request: Request) -> MarketDataProvider:
    """Retrieve the shared market data provider from the application state."""
    return cast(MarketDataProvider, request.app.state.provider)


def get_backtest_service(request: Request) -> BacktestService:
    """Access the backtest service stored on the FastAPI application."""
    return cast(BacktestService, request.app.state.backtest_service)


def get_finance_service(request: Request) -> FinanceDataService:
    """Return the cached finance data service."""
    return cast(FinanceDataService, request.app.state.finance_service)


@router.get(
    "/quote",
    response_model=QuoteResponse,
    summary="Retrieve a quote snapshot",
    description="Renvoie un instantané prix/variation pour un symbole suivi par le service finance.",
    response_description="Dernière cotation connue du symbole demandé.",
)
def get_quote(
    query: Annotated[QuoteQuery, Depends()],
    service: Annotated[FinanceDataService, Depends(get_finance_service)],
) -> QuoteResponse:
    """Return a price snapshot for the requested symbol."""
    snapshot = service.get_quote(query.symbol)
    return QuoteResponse(
        symbol=query.symbol,
        price=snapshot.price,
        changePct=snapshot.change_pct,
        currency=snapshot.currency,
        updatedAt=snapshot.updated_at,
    )


@router.get(
    "/fundamentals",
    response_model=FundamentalsResponse,
    summary="Load fundamentals for a symbol",
    description="Expose un sous-ensemble de métriques fondamentales pré-agrégées.",
    response_description="Données fondamentales prêtes à l'affichage.",
)
def get_fundamentals(
    query: Annotated[FundamentalsQuery, Depends()],
    service: Annotated[FinanceDataService, Depends(get_finance_service)],
) -> FundamentalsResponse:
    """Return a curated set of fundamentals for the symbol."""
    fundamentals = service.get_fundamentals(query.symbol)
    return FundamentalsResponse(
        symbol=query.symbol,
        marketCap=fundamentals.market_cap,
        peRatio=fundamentals.pe_ratio,
        dividendYield=fundamentals.dividend_yield,
        week52High=fundamentals.week52_high,
        week52Low=fundamentals.week52_low,
    )


@router.get(
    "/news",
    response_model=NewsResponse,
    summary="List curated finance news",
    description="Retourne des actualités chronologiques provenant du cache finance déterministe.",
    response_description="Articles triés par date décroissante.",
)
def get_news(
    query: Annotated[NewsQuery, Depends()],
    service: Annotated[FinanceDataService, Depends(get_finance_service)],
) -> NewsResponse:
    """Return chronological finance news for the symbol."""
    articles = service.get_news(query.symbol, limit=query.limit, offset=query.offset)
    items = [
        NewsItemModel(
            id=article.id,
            title=article.title,
            url=article.url,
            publishedAt=article.published_at,
        )
        for article in articles
    ]
    return NewsResponse(symbol=query.symbol, items=items)


@router.get(
    "/screen",
    response_model=ScreenResponse,
    summary="Run the deterministic screener",
    description="Applique les filtres sectoriels/score pour retourner des actifs présélectionnés.",
    response_description="Résultats de screener ordonnés.",
)
def get_screen(
    query: Annotated[ScreenQuery, Depends()],
    service: Annotated[FinanceDataService, Depends(get_finance_service)],
) -> ScreenResponse:
    """Return screener results filtered by optional criteria."""
    results = service.screen(sector=query.sector, min_score=query.min_score, limit=query.limit)
    serialized = [
        ScreenedAssetModel(
            symbol=asset.symbol,
            sector=asset.sector,
            score=asset.score,
            marketCap=asset.market_cap,
        )
        for asset in results
    ]
    return ScreenResponse(results=serialized)


@router.post(
    "/backtest",
    response_model=BacktestResponse,
    summary="Execute a backtest scenario",
    description="Lance le moteur de backtest interne avec paramètres de stratégie, frais et slippage.",
    response_description="Résultat complet du backtest (équité, métriques, trades).",
)
def run_backtest(
    payload: BacktestRequest,
    provider: Annotated[MarketDataProvider, Depends(get_provider)],
    service: Annotated[BacktestService, Depends(get_backtest_service)],
) -> BacktestResponse:
    """Execute a backtest with the provided strategy parameters."""
    result = service.run(
        provider,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        fees_bps=payload.fees_bps,
        slippage_bps=payload.slippage_bps,
        strategy=payload.strategy,
    )
    return _serialize_backtest(payload.symbol, payload.timeframe, result)


def _serialize_backtest(symbol: str, timeframe: str, result: BacktestResult) -> BacktestResponse:
    """Convert the service result into the API response schema."""
    metrics_model = MetricsModel(**result.metrics.__dict__)
    trades = [
        TradeModel(
            entryTs=trade.entry_ts,
            exitTs=trade.exit_ts,
            entryPrice=trade.entry_price,
            exitPrice=trade.exit_price,
            returnPct=trade.return_pct,
        )
        for trade in result.trades
    ]
    equity_curve = [EquityPoint(ts=ts, equity=equity) for ts, equity in result.equity_curve]
    return BacktestResponse(
        symbol=symbol,
        timeframe=timeframe,
        metrics=metrics_model,
        equityCurve=equity_curve,
        trades=trades,
    )


@router.get(
    "/chart",
    response_model=ChartArtifactResponse,
    summary="Build a chart artefact",
    description="Assemble un artefact de graphique (statistiques, overlays, chandelles enrichies).",
    response_description="Artefact détaillé prêt pour le front finance.",
)
def get_chart_artifact(
    query: Annotated[ChartArtifactQuery, Depends()],
    provider: Annotated[MarketDataProvider, Depends(get_provider)],
    service: Annotated[FinanceDataService, Depends(get_finance_service)],
    overlays_payload: Annotated[str | None, Query(alias="overlays")] = None,
) -> ChartArtifactResponse:
    """Return a defensive chart artefact payload with derived candle metrics."""
    frame = provider.get_ohlcv(
        query.symbol,
        query.timeframe,
        limit=query.limit,
        start=query.resolved_start(),
        end=query.resolved_end(),
    )
    rows = normalize_ohlcv_frame(frame)
    overlay_models: list[ChartOverlayToggle] = []
    if overlays_payload:
        try:
            parsed_payload = json.loads(overlays_payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise BadRequest("overlays must be valid JSON") from exc
        if not isinstance(parsed_payload, list):
            raise BadRequest("overlays must be an array")
        if len(parsed_payload) > 4:
            raise BadRequest("Up to four overlays can be requested at once")
        overlay_models = [ChartOverlayToggle.model_validate(item) for item in parsed_payload]
        identifiers = {overlay.id for overlay in overlay_models}
        if len(identifiers) != len(overlay_models):
            raise BadRequest("Overlay identifiers must be unique")

    overlay_requests = [
        OverlayRequest(identifier=overlay.id, kind=overlay.type, window=overlay.window)
        for overlay in overlay_models
    ]
    summary = service.build_chart_artifact(
        rows,
        selected_ts=query.selected_ts,
        overlays=overlay_requests,
    )

    range_model = (
        ChartRangeModel(
            firstTs=summary.range.first_ts,
            lastTs=summary.range.last_ts,
            high=summary.range.high,
            low=summary.range.low,
            totalVolume=summary.range.total_volume,
        )
        if summary.range
        else None
    )

    def _to_candle_model(snapshot: ChartCandleSnapshot) -> ChartCandleDetails:
        """Convert a domain snapshot into the API schema model."""
        return ChartCandleDetails(
            ts=snapshot.ts,
            open=snapshot.open,
            high=snapshot.high,
            low=snapshot.low,
            close=snapshot.close,
            volume=snapshot.volume,
            previousClose=snapshot.previous_close,
            changeAbs=snapshot.change_abs,
            changePct=snapshot.change_pct,
            range=snapshot.trading_range,
            body=snapshot.body,
            bodyPct=snapshot.body_pct,
            upperWick=snapshot.upper_wick,
            lowerWick=snapshot.lower_wick,
            direction=snapshot.direction,
        )

    selected_model = _to_candle_model(summary.selected) if summary.selected else None
    detail_models = [_to_candle_model(detail) for detail in summary.details]

    overlays = [
        OverlaySeriesModel(
            id=overlay.identifier,
            type=overlay.kind,
            window=overlay.window,
            points=[OverlayPointModel(ts=point.ts, value=point.value) for point in overlay.points],
        )
        for overlay in summary.overlays
    ]

    return ChartArtifactResponse(
        status=summary.status,
        symbol=query.symbol,
        timeframe=query.timeframe,
        rows=list(summary.rows),
        range=range_model,
        selected=selected_model,
        details=detail_models,
        overlays=overlays,
    )


__all__ = ["router"]
