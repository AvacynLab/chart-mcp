"""FastAPI application factory for chart_mcp."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from chart_mcp.config import settings
from chart_mcp.routes import (
    analysis,
    health,
    indicators,
    levels,
    market,
    patterns,
    stream,
)
from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.services.indicators import IndicatorService
from chart_mcp.services.levels import LevelsService
from chart_mcp.services.patterns import PatternsService
from chart_mcp.services.streaming import StreamingService
from chart_mcp.utils.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unexpected_exception_handler,
)
from chart_mcp.utils.logging import configure_logging, logging_middleware


def create_app() -> FastAPI:
    """Instantiate FastAPI application with configured routes and services."""
    configure_logging()
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
    app.middleware("http")(logging_middleware)

    provider = CcxtDataProvider()
    indicator_service = IndicatorService()
    levels_service = LevelsService()
    patterns_service = PatternsService()
    analysis_service = AnalysisLLMService()
    streaming_service = StreamingService(
        provider, indicator_service, levels_service, patterns_service, analysis_service
    )

    app.state.provider = provider
    app.state.indicator_service = indicator_service
    app.state.levels_service = levels_service
    app.state.patterns_service = patterns_service
    app.state.analysis_service = analysis_service
    app.state.streaming_service = streaming_service

    app.include_router(health.router)
    app.include_router(market.router)
    app.include_router(indicators.router)
    app.include_router(levels.router)
    app.include_router(patterns.router)
    app.include_router(analysis.router)
    app.include_router(stream.router)

    app.add_exception_handler(Exception, unexpected_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ApiError, api_error_handler)

    return app


app = create_app()
