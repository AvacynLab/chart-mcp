"""FastAPI application factory for chart_mcp."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from chart_mcp.config import get_settings
from chart_mcp.routes import (
    analysis,
    finance,
    health,
    indicators,
    levels,
    market,
    patterns,
    stream,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.backtest import BacktestService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.services.finance import PLAYWRIGHT_REFERENCE_TIME, default_finance_service
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unexpected_exception_handler,
)
from chart_mcp.utils.logging import configure_logging, logging_middleware
from chart_mcp.utils.ratelimit import RateLimiter, RateLimitMiddleware


def create_app() -> FastAPI:
    """Instantiate FastAPI application with configured routes and services."""
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="chart-mcp", version="0.1.0")
    allowed_origins = settings.allowed_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # The limiter protects public routes while allowing Playwright scenarios to bypass quotas
    # so that deterministic E2E suites can drive the API without spurious 429 responses.
    limiter = RateLimiter(
        settings.rate_limit_per_minute,
        bypass=settings.playwright_mode,
    )
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    app.middleware("http")(logging_middleware)

    provider = CcxtDataProvider()
    indicator_service = IndicatorService()
    levels_service = LevelsService()
    patterns_service = PatternsService()
    analysis_service = AnalysisLLMService()
    backtest_service = BacktestService()
    streaming_service = StreamingService(
        provider, indicator_service, levels_service, patterns_service, analysis_service
    )
    app.state.provider = provider
    app.state.indicator_service = indicator_service
    app.state.levels_service = levels_service
    app.state.patterns_service = patterns_service
    app.state.analysis_service = analysis_service
    app.state.backtest_service = backtest_service
    app.state.streaming_service = streaming_service

    finance_feature_enabled = settings.feature_finance
    # The finance feature flag lets operators disable advanced artefacts without
    # touching routing code elsewhere. When disabled the dedicated router is not
    # mounted and the state entry is set to ``None`` so dependency injection will
    # fail fast if referenced by mistake during tests.
    reference_now = (
        PLAYWRIGHT_REFERENCE_TIME if settings.playwright_mode else datetime.now(tz=timezone.utc)
    )
    finance_service = (
        default_finance_service(now=reference_now) if finance_feature_enabled else None
    )
    app.state.finance_service = finance_service

    app.include_router(health.router)
    app.include_router(market.router)
    if finance_feature_enabled:
        app.include_router(finance.router)
    app.include_router(indicators.router)
    app.include_router(levels.router)
    app.include_router(patterns.router)
    app.include_router(analysis.router)
    app.include_router(stream.router)

    app.add_exception_handler(Exception, unexpected_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    return app


app = create_app()
