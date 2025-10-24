"""Unit tests for :mod:`chart_mcp.services.finance`."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pandas as pd
import pytest

from chart_mcp.schemas.market import OhlcvRow
from chart_mcp.services.finance import (
    PLAYWRIGHT_REFERENCE_TIME,
    FinanceDataService,
    FundamentalsSnapshot,
    NewsArticle,
    OverlayRequest,
    QuoteSnapshot,
    ScreenedAsset,
    default_finance_service,
)
from chart_mcp.utils.errors import BadRequest, NotFound


@pytest.fixture()
def service() -> FinanceDataService:
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return FinanceDataService(
        quotes={
            "AAPL": QuoteSnapshot(price=180.0, change_pct=0.5, currency="USD", updated_at=base_time)
        },
        fundamentals={
            "AAPL": FundamentalsSnapshot(
                market_cap=2.5e12,
                pe_ratio=27.0,
                dividend_yield=0.006,
                week52_high=195.0,
                week52_low=120.0,
            )
        },
        news={
            "AAPL": [
                NewsArticle(
                    id="aapl-older",
                    title="Older headline",
                    url="https://example.com/older",
                    published_at=base_time.replace(hour=8),
                ),
                NewsArticle(
                    id="aapl-new",
                    title="New headline",
                    url="https://example.com/new",
                    published_at=base_time.replace(hour=10),
                ),
            ]
        },
        screened_assets=[
            ScreenedAsset(symbol="AAPL", sector="Technology", score=0.8, market_cap=2.5e12),
            ScreenedAsset(symbol="MSFT", sector="Technology", score=0.85, market_cap=2.3e12),
        ],
    )


def test_get_quote_normalizes_symbol(service: FinanceDataService) -> None:
    snapshot = service.get_quote("aapl")
    assert snapshot.price == 180.0


def test_get_quote_missing_symbol_raises(service: FinanceDataService) -> None:
    with pytest.raises(NotFound):
        service.get_quote("msft")


def test_get_news_respects_limit_and_order(service: FinanceDataService) -> None:
    articles = service.get_news("AAPL", limit=1, offset=0)
    assert len(articles) == 1
    assert articles[0].id == "aapl-new"


def test_get_news_rejects_invalid_limit(service: FinanceDataService) -> None:
    with pytest.raises(BadRequest):
        service.get_news("AAPL", limit=0)


def test_screen_filters_by_score_and_limit(service: FinanceDataService) -> None:
    results = service.screen(sector="Technology", min_score=0.81, limit=1)
    assert len(results) == 1
    assert results[0].symbol == "MSFT"


def test_screen_rejects_invalid_limit(service: FinanceDataService) -> None:
    with pytest.raises(BadRequest):
        service.screen(limit=0)


def test_default_finance_service_respects_injected_time() -> None:
    """Ensure the canned finance fixtures can operate with a frozen clock."""
    frozen = datetime(2025, 1, 2, 15, tzinfo=timezone.utc)
    service = default_finance_service(now=frozen)
    snapshot = service.get_quote("BTCUSD")
    assert snapshot.updated_at == frozen
    article = service.get_news("BTCUSD", limit=1)[0]
    # BTC news is pegged to the day before the reference timestamp.
    assert article.published_at.day == max(1, frozen.day - 1)


def test_default_finance_service_uses_reference_constant() -> None:
    """Playwright scenarios rely on a stable fixture timestamp for determinism."""
    service = default_finance_service(now=PLAYWRIGHT_REFERENCE_TIME)
    snapshot = service.get_quote("NVDA")
    assert snapshot.updated_at == PLAYWRIGHT_REFERENCE_TIME


def test_build_chart_artifact_handles_empty_payload(service: FinanceDataService) -> None:
    """The chart helper should gracefully handle providers returning no rows."""
    summary = service.build_chart_artifact([], selected_ts=None)
    assert summary.status == "empty"
    assert summary.rows == ()
    assert summary.range is None
    assert summary.selected is None
    assert summary.details == ()


def test_build_chart_artifact_derives_metrics(service: FinanceDataService) -> None:
    """Ensure derived fields are computed for the selected candle."""
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=1, o=10.0, h=11.0, l=9.5, c=10.5, v=100.0),
        OhlcvRow(ts=2, o=10.5, h=12.0, l=10.2, c=11.5, v=150.0),
        OhlcvRow(ts=3, o=11.5, h=12.5, l=11.0, c=11.0, v=120.0),
    ]
    summary = service.build_chart_artifact(rows, selected_ts=2)
    assert summary.status == "ready"
    assert summary.range is not None
    assert summary.range.first_ts == 1
    assert summary.range.last_ts == 3
    assert summary.range.high == pytest.approx(12.5)
    assert summary.range.low == pytest.approx(9.5)
    assert summary.range.total_volume == pytest.approx(370.0)

    assert summary.selected is not None
    assert summary.selected.ts == 2
    assert summary.selected.previous_close == pytest.approx(10.5)
    assert summary.selected.change_abs == pytest.approx(1.0)
    assert summary.selected.change_pct == pytest.approx(9.5238, rel=1e-4)
    # Body/wick analytics are computed server-side to keep the UI lightweight.
    assert summary.selected.trading_range == pytest.approx(12.0 - 10.2)
    assert summary.selected.body == pytest.approx(1.0)
    assert summary.selected.body_pct == pytest.approx((1.0 / 10.5) * 100)
    assert summary.selected.upper_wick == pytest.approx(12.0 - 11.5)
    assert summary.selected.lower_wick == pytest.approx(10.5 - 10.2)
    assert summary.selected.direction == "bullish"
    assert len(summary.details) == len(rows)
    assert summary.details[1] == summary.selected
    assert summary.details[2].direction == "bearish"


def test_build_chart_artifact_details_use_previous_close(service: FinanceDataService) -> None:
    """Every candle detail should reference the preceding close when available."""
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=1, o=10.0, h=11.0, l=9.5, c=10.5, v=100.0),
        OhlcvRow(ts=2, o=10.5, h=12.0, l=10.2, c=11.5, v=150.0),
    ]
    summary = service.build_chart_artifact(rows, selected_ts=None)

    assert len(summary.details) == 2
    first, second = summary.details
    # The first candle falls back to its open price, preventing a divide-by-zero
    # when no prior close exists.
    assert first.previous_close == pytest.approx(rows[0].open)
    assert first.change_abs == pytest.approx(rows[0].close - rows[0].open)
    expected_first_pct = 0.0 if rows[0].open == 0 else (
        (rows[0].close - rows[0].open) / rows[0].open
    ) * 100
    assert first.change_pct == pytest.approx(expected_first_pct)
    assert first.trading_range == pytest.approx(rows[0].high - rows[0].low)
    assert first.upper_wick >= 0
    assert first.lower_wick >= 0
    assert first.direction == ("bullish" if rows[0].close > rows[0].open else "neutral")
    # Subsequent candles must use the previous close, mirroring tooltip maths
    # expected by charting libraries.
    assert second.previous_close == pytest.approx(rows[0].close)
    assert second.change_abs == pytest.approx(rows[1].close - rows[0].close)
    expected_pct = 0.0 if rows[0].close == 0 else (
        (rows[1].close - rows[0].close) / rows[0].close
    ) * 100
    assert second.change_pct == pytest.approx(expected_pct)
    assert second.direction == "bullish"


def test_build_chart_artifact_includes_sma_overlay(service: FinanceDataService) -> None:
    """Requesting an SMA overlay should return the rolling averages per candle."""
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=1, o=10.0, h=11.0, l=9.5, c=10.5, v=100.0),
        OhlcvRow(ts=2, o=10.5, h=12.0, l=10.2, c=11.5, v=150.0),
        OhlcvRow(ts=3, o=11.5, h=12.5, l=11.0, c=11.0, v=120.0),
    ]
    summary = service.build_chart_artifact(
        rows,
        overlays=[OverlayRequest(identifier="sma-2", kind="sma", window=2)],
    )

    assert len(summary.overlays) == 1
    overlay = summary.overlays[0]
    assert overlay.identifier == "sma-2"
    assert overlay.window == 2
    assert overlay.points[0].value is None
    assert overlay.points[1].value == pytest.approx(11.0)
    assert overlay.points[2].value == pytest.approx(11.25)


def test_build_chart_artifact_includes_ema_overlay(service: FinanceDataService) -> None:
    """EMA overlays should mirror the pandas ewm computation used by the UI."""
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=1, o=10.0, h=11.0, l=9.5, c=10.5, v=100.0),
        OhlcvRow(ts=2, o=10.5, h=12.0, l=10.2, c=11.5, v=150.0),
        OhlcvRow(ts=3, o=11.5, h=12.5, l=11.0, c=11.0, v=120.0),
    ]
    summary = service.build_chart_artifact(
        rows,
        overlays=[OverlayRequest(identifier="ema-2", kind="ema", window=2)],
    )

    frame = pd.DataFrame({
        "ts": [row.ts for row in rows],
        "o": [row.open for row in rows],
        "h": [row.high for row in rows],
        "l": [row.low for row in rows],
        "c": [row.close for row in rows],
        "v": [row.volume for row in rows],
    }).set_index("ts")
    expected = frame["c"].ewm(span=2, adjust=False).mean()

    overlay = summary.overlays[0]
    assert overlay.kind == "ema"
    assert [point.ts for point in overlay.points] == list(expected.index)
    for point, expected_value in zip(overlay.points, expected.tolist(), strict=True):
        assert point.value == pytest.approx(expected_value)


def test_build_chart_artifact_overlay_validates_window(service: FinanceDataService) -> None:
    """Windows larger than the available data should bubble a :class:`BadRequest`."""
    rows: List[OhlcvRow] = [
        OhlcvRow(ts=1, o=10.0, h=11.0, l=9.5, c=10.5, v=100.0),
        OhlcvRow(ts=2, o=10.5, h=12.0, l=10.2, c=11.5, v=150.0),
    ]
    with pytest.raises(BadRequest):
        service.build_chart_artifact(
            rows,
            overlays=[OverlayRequest(identifier="sma-5", kind="sma", window=5)],
        )

