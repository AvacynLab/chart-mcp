"""FastAPI application factory for chart_mcp."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from chart_mcp.config import get_settings
from chart_mcp.routes import (
    analysis,
    finance,
    health,
    indicators,
    levels,
    market,
    metrics,
    patterns,
    search,
    stream,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.backtest import BacktestService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.services.finance import PLAYWRIGHT_REFERENCE_TIME, default_finance_service
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.services.search import SearxNGClient
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

# Metadata used to document the public FastAPI surface in the generated OpenAPI
# specification. Providing explicit descriptions keeps the interactive Swagger
# UI and the README in sync and satisfies the documentation requirements from
# the product brief.
OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Monitoring endpoints exposing uptime and build metadata.",
    },
    {
        "name": "market",
        "description": "Raw market data retrieval such as normalized OHLCV candles.",
    },
    {
        "name": "indicators",
        "description": "Technical indicator computations based on OHLCV history.",
    },
    {
        "name": "levels",
        "description": "Support and resistance level detection with strength scoring.",
    },
    {
        "name": "patterns",
        "description": "Chart pattern detection including head-and-shoulders heuristics.",
    },
    {
        "name": "analysis",
        "description": "Aggregated analysis summaries mixing indicators, levels and patterns.",
    },
    {
        "name": "finance",
        "description": "Optional finance utilities such as fundamentals, screeners and backtests.",
    },
    {
        "name": "search",
        "description": "SearxNG-backed discovery of crypto news, documentation and research.",
    },
    {
        "name": "stream",
        "description": "Server-Sent Events surfaces streaming the multi-step analysis pipeline.",
    },
]


def create_app() -> FastAPI:
    """Instantiate FastAPI application with configured routes and services."""
    configure_logging()
    settings = get_settings()
    # Rely on ``ORJSONResponse`` for the default responses to keep JSON
    # serialization fast while maintaining feature parity with the standard
    # encoder used previously.
    app = FastAPI(
        title="chart-mcp",
        description=(
            "API FastAPI pour le Market Charting Pipeline : données crypto, indicateurs, "
            "niveaux, figures chartistes et flux SSE tokenisé."
        ),
        version="0.1.0",
        default_response_class=ORJSONResponse,
        openapi_tags=OPENAPI_TAGS,
    )
    # Respect the exact origin list configured by operators so production deployments
    # never default to permissive wildcard CORS headers.
    allowed_origins = list(settings.allowed_origins)
    if not allowed_origins:
        if settings.playwright_mode:
            # Test and development environments may omit ALLOWED_ORIGINS. In that
            # scenario we default to the local Next.js frontend origin so the
            # developer experience stays smooth while keeping the production
            # contract strict.
            allowed_origins = ["http://localhost:3000"]
        else:
            raise RuntimeError(
                "ALLOWED_ORIGINS must define at least one origin for production deployments"
            )
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
    finance_feature_enabled = settings.feature_finance
    reference_now = (
        PLAYWRIGHT_REFERENCE_TIME if settings.playwright_mode else datetime.now(tz=timezone.utc)
    )
    base_finance_service = default_finance_service(now=reference_now)
    streaming_service = StreamingService(
        provider,
        indicator_service,
        levels_service,
        patterns_service,
        analysis_service,
        finance_service=base_finance_service,
    )
    # The optional search client proxies aggregation requests to the companion
    # SearxNG container. When operators omit the base URL the HTTP route will
    # surface a clear 400 error instructing them to configure the integration.
    search_client = (
        SearxNGClient(settings.searxng_base_url, timeout=settings.searxng_timeout)
        if settings.searxng_base_url
        else None
    )
    app.state.provider = provider
    app.state.indicator_service = indicator_service
    app.state.levels_service = levels_service
    app.state.patterns_service = patterns_service
    app.state.analysis_service = analysis_service
    app.state.backtest_service = backtest_service
    app.state.streaming_service = streaming_service
    app.state.search_client = search_client

    # The finance feature flag lets operators disable advanced artefacts without
    # touching routing code elsewhere. When disabled the dedicated router is not
    # mounted and the state entry is set to ``None`` so dependency injection will
    # fail fast if referenced by mistake during tests.
    app.state.finance_service = base_finance_service if finance_feature_enabled else None

    app.include_router(health.router)
    app.include_router(market.router)
    app.include_router(metrics.router)
    if finance_feature_enabled:
        app.include_router(finance.router)
    app.include_router(indicators.router)
    app.include_router(levels.router)
    app.include_router(patterns.router)
    app.include_router(analysis.router)
    app.include_router(search.router)
    app.include_router(stream.router)

    app.add_exception_handler(Exception, unexpected_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    return app


app = create_app()
