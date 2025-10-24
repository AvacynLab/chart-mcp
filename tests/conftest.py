"""Test fixtures for chart_mcp."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

os.environ.setdefault("API_TOKEN", "testingtoken")
os.environ.setdefault("PLAYWRIGHT", "true")
os.environ.setdefault("FEATURE_FINANCE", "true")

from chart_mcp.app import create_app  # noqa: E402
from chart_mcp.services.analysis_llm import AnalysisLLMService  # noqa: E402
from chart_mcp.services.backtest import BacktestService  # noqa: E402
from chart_mcp.services.data_providers.base import MarketDataProvider  # noqa: E402
from chart_mcp.services.finance import (
    FinanceDataService,
    FundamentalsSnapshot,
    NewsArticle,
    QuoteSnapshot,
    ScreenedAsset,
)
from chart_mcp.services.indicators import IndicatorService  # noqa: E402
from chart_mcp.services.levels import LevelsService  # noqa: E402
from chart_mcp.services.patterns import PatternsService  # noqa: E402


class FakeProvider(MarketDataProvider):
    """Deterministic provider returning synthetic OHLCV data for tests."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.client = type("Client", (), {"id": "stub"})()

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
        start: int | None = None,
        end: int | None = None,
    ) -> pd.DataFrame:
        """Return a copy of the synthetic OHLCV frame sliced by limit and range."""
        frame = self.frame.copy().head(limit)
        if start:
            frame = frame[frame["ts"] >= start]
        if end:
            frame = frame[frame["ts"] <= end]
        return frame.reset_index(drop=True)


@pytest.fixture(scope="session")
def ohlcv_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    base_ts = int(datetime(2024, 1, 1).timestamp())
    timestamps = np.arange(base_ts, base_ts + 3600 * 200, 3600)
    prices = 100 + np.sin(np.linspace(0, 6 * np.pi, len(timestamps))) * 5
    frame = pd.DataFrame(
        {
            "ts": timestamps,
            "o": prices + rng.uniform(-0.5, 0.5, len(prices)),
            "h": prices + 1,
            "l": prices - 1,
            "c": prices,
            "v": rng.uniform(50, 150, len(prices)),
        }
    )
    return frame


@pytest.fixture()
def test_app(ohlcv_frame: pd.DataFrame):
    app = create_app()
    provider = FakeProvider(ohlcv_frame)
    indicator_service = IndicatorService()
    levels_service = LevelsService()
    patterns_service = PatternsService()
    analysis_service = AnalysisLLMService()
    backtest_service = BacktestService()
    base_time = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    finance_service = FinanceDataService(
        quotes={
            "BTCUSD": QuoteSnapshot(price=65000.0, change_pct=1.5, currency="USD", updated_at=base_time),
            "NVDA": QuoteSnapshot(price=900.0, change_pct=2.0, currency="USD", updated_at=base_time),
        },
        fundamentals={
            "BTCUSD": FundamentalsSnapshot(
                market_cap=1.2e12,
                pe_ratio=0.0,
                dividend_yield=0.0,
                week52_high=72000.0,
                week52_low=30000.0,
            ),
            "NVDA": FundamentalsSnapshot(
                market_cap=2.1e12,
                pe_ratio=34.0,
                dividend_yield=0.0,
                week52_high=950.0,
                week52_low=350.0,
            ),
        },
        news={
            "NVDA": [
                NewsArticle(
                    id="nvda-1",
                    title="NVDA launches new GPU",
                    url="https://example.com/nvda-gpu",
                    published_at=base_time,
                ),
                NewsArticle(
                    id="nvda-0",
                    title="Analysts raise NVDA targets",
                    url="https://example.com/nvda-analyst",
                    published_at=base_time.replace(hour=8),
                ),
            ]
        },
        screened_assets=[
            ScreenedAsset(symbol="NVDA", sector="Technology", score=0.9, market_cap=2.1e12),
            ScreenedAsset(symbol="BTCUSD", sector="Crypto", score=0.85, market_cap=1.2e12),
        ],
    )
    app.state.provider = provider
    app.state.indicator_service = indicator_service
    app.state.levels_service = levels_service
    app.state.patterns_service = patterns_service
    app.state.analysis_service = analysis_service
    app.state.backtest_service = backtest_service
    app.state.finance_service = finance_service
    streaming_service = app.state.streaming_service
    streaming_service.provider = provider
    streaming_service.indicator_service = indicator_service
    streaming_service.levels_service = levels_service
    streaming_service.patterns_service = patterns_service
    streaming_service.analysis_service = analysis_service
    return app


@pytest.fixture()
def client(test_app):
    with TestClient(test_app) as client:
        client.headers.update(
            {
                "Authorization": "Bearer testingtoken",
                "X-User-Type": "regular",
            }
        )
        yield client
