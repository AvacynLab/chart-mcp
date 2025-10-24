"""Domain service exposing quote, fundamentals, news and screener data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Iterable, List, Literal, Optional, Sequence

import pandas as pd

from chart_mcp.services.indicators import (
    exponential_moving_average,
    simple_moving_average,
)
from chart_mcp.utils.errors import BadRequest, NotFound

if TYPE_CHECKING:  # pragma: no cover - used only for type checking imports
    from chart_mcp.schemas.market import OhlcvRow


@dataclass(frozen=True)
class QuoteSnapshot:
    """Single quote snapshot containing pricing metadata."""

    price: float
    change_pct: float
    currency: str
    updated_at: datetime


@dataclass(frozen=True)
class FundamentalsSnapshot:
    """Aggregated fundamental metrics for a symbol."""

    market_cap: float
    pe_ratio: float
    dividend_yield: float
    week52_high: float
    week52_low: float


@dataclass(frozen=True)
class NewsArticle:
    """Lightweight representation of a finance news article."""

    id: str
    title: str
    url: str
    published_at: datetime


@dataclass(frozen=True)
class ScreenedAsset:
    """Result returned by the screener with ranking metadata."""

    symbol: str
    sector: str
    score: float
    market_cap: float


@dataclass(frozen=True)
class ChartRangeSnapshot:
    """Aggregate boundaries and volume for a batch of OHLCV rows."""

    first_ts: int
    last_ts: int
    high: float
    low: float
    total_volume: float


@dataclass(frozen=True)
class ChartCandleSnapshot:
    """Detailed metrics for a single candle used by the chart artifact.

    The snapshot mirrors the UI expectations by surfacing price change figures,
    body/wick analytics and a direction tag so front-end components can render
    tooltips without duplicating trading-specific calculations.
    """

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    previous_close: float
    change_abs: float
    change_pct: float
    trading_range: float
    body: float
    body_pct: float
    upper_wick: float
    lower_wick: float
    direction: Literal["bullish", "bearish", "neutral"]


@dataclass(frozen=True)
class ChartArtifactSummary:
    """Structured representation returned by :meth:`FinanceDataService.build_chart_artifact`."""

    status: Literal["empty", "ready"]
    rows: Sequence["OhlcvRow"]
    range: Optional[ChartRangeSnapshot]
    selected: Optional[ChartCandleSnapshot]
    details: Sequence[ChartCandleSnapshot] = field(default_factory=tuple)
    overlays: Sequence["OverlaySeriesSnapshot"] = field(default_factory=tuple)


@dataclass(frozen=True)
class OverlayPointSnapshot:
    """Single point composing an overlay time-series."""

    ts: int
    value: float | None


@dataclass(frozen=True)
class OverlaySeriesSnapshot:
    """Computed overlay series used to draw SMA/EMA lines on the chart."""

    identifier: str
    kind: Literal["sma", "ema"]
    window: int
    points: Sequence[OverlayPointSnapshot]


@dataclass(frozen=True)
class OverlayRequest:
    """Descriptor of an overlay requested by the UI layer."""

    identifier: str
    kind: Literal["sma", "ema"]
    window: int


class FinanceDataService:
    """Provide deterministic finance payloads consumed by the HTTP API."""

    def __init__(
        self,
        *,
        quotes: Dict[str, QuoteSnapshot] | None = None,
        fundamentals: Dict[str, FundamentalsSnapshot] | None = None,
        news: Dict[str, Sequence[NewsArticle]] | None = None,
        screened_assets: Sequence[ScreenedAsset] | None = None,
    ) -> None:
        """Store lookup tables used to serve deterministic responses."""
        self._quotes = {symbol.upper(): snapshot for symbol, snapshot in (quotes or {}).items()}
        self._fundamentals = {
            symbol.upper(): snapshot for symbol, snapshot in (fundamentals or {}).items()
        }
        self._news = {symbol.upper(): list(articles) for symbol, articles in (news or {}).items()}
        self._screened_assets = list(screened_assets or ())

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Return the canonical symbol identifier used for lookups."""
        if not symbol:
            raise BadRequest("Symbol must be provided")
        if len(symbol) < 2 or len(symbol) > 20:
            raise BadRequest("Symbol length must be between 2 and 20 characters")
        return symbol.upper()

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        """Return a quote snapshot for *symbol* or raise :class:`NotFound`."""
        key = self._normalize_symbol(symbol)
        try:
            return self._quotes[key]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise NotFound(f"Quote not available for {key}") from exc

    def get_fundamentals(self, symbol: str) -> FundamentalsSnapshot:
        """Return fundamental metrics for *symbol* or raise :class:`NotFound`."""
        key = self._normalize_symbol(symbol)
        try:
            return self._fundamentals[key]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise NotFound(f"Fundamentals not available for {key}") from exc

    def get_news(self, symbol: str, *, limit: int, offset: int = 0) -> List[NewsArticle]:
        """Return chronological news for *symbol* bounded by ``limit`` and ``offset``."""
        if limit <= 0 or limit > 50:
            raise BadRequest("limit must be between 1 and 50")
        if offset < 0:
            raise BadRequest("offset must be positive")
        key = self._normalize_symbol(symbol)
        articles = self._news.get(key)
        if articles is None:
            raise NotFound(f"News not available for {key}")
        # Sort newest-first so pagination remains deterministic.
        sorted_articles = sorted(articles, key=lambda article: article.published_at, reverse=True)
        return sorted_articles[offset : offset + limit]

    def screen(
        self,
        *,
        sector: str | None = None,
        min_score: float = 0.0,
        limit: int = 20,
    ) -> List[ScreenedAsset]:
        """Return screener matches optionally filtered by ``sector`` and ``min_score``."""
        if limit <= 0 or limit > 100:
            raise BadRequest("limit must be between 1 and 100")
        if min_score < 0 or min_score > 1:
            raise BadRequest("minScore must be between 0 and 1")
        # Filtering is done eagerly on a snapshot to avoid mutating the cached list.
        filtered: Iterable[ScreenedAsset] = self._screened_assets
        if sector:
            filtered = (asset for asset in filtered if asset.sector.lower() == sector.lower())
        filtered = (asset for asset in filtered if asset.score >= min_score)
        results = sorted(filtered, key=lambda asset: asset.score, reverse=True)
        return results[:limit]

    def build_chart_artifact(
        self,
        rows: Sequence["OhlcvRow"],
        *,
        selected_ts: int | None = None,
        overlays: Sequence[OverlayRequest] | None = None,
    ) -> ChartArtifactSummary:
        """Summarise normalized OHLCV rows for the finance chart artefact.

        Parameters
        ----------
        rows:
            Normalised OHLCV candles previously sanitised by
            :func:`chart_mcp.utils.data_adapter.normalize_ohlcv_frame`.
        selected_ts:
            Optional timestamp (in seconds) identifying the candle to
            highlight. When omitted or missing from *rows*, the most recent
            candle is used instead.
        overlays:
            Optional collection of overlay descriptors (e.g. SMA/EMA) requested
            by the caller. Each descriptor is converted into a numeric series so
            the UI can toggle the overlays without fetching additional data.

        Notes
        -----
        The method defensively handles empty datasets and zero-valued closing
        prices to ensure the front-end never encounters divide-by-zero errors
        when computing percentage deltas. This keeps the React chart component
        resilient when the provider returns sparse or truncated data.

        """
        if not rows:
            return ChartArtifactSummary(
                status="empty",
                rows=(),
                range=None,
                selected=None,
                details=(),
                overlays=(),
            )

        sorted_rows = sorted(rows, key=lambda row: row.ts)
        selected_index = None
        if selected_ts is not None:
            for index, row in enumerate(sorted_rows):
                if row.ts == selected_ts:
                    selected_index = index
                    break
        if selected_index is None:
            selected_index = len(sorted_rows) - 1

        detail_snapshots: List[ChartCandleSnapshot] = []
        # The first candle uses its own open price as the baseline. Each
        # subsequent candle references the previous close so the derived change
        # metrics mirror what a trading terminal would display when hovering a
        # chart. While iterating we also compute body/wick analytics that the UI
        # can surface without reimplementing trading maths client-side.
        previous_close_value = None
        for index, row in enumerate(sorted_rows):
            if index == 0 or previous_close_value is None:
                baseline = row.open
            else:
                baseline = previous_close_value
            change_abs = row.close - baseline
            change_pct = 0.0 if baseline == 0 else (change_abs / baseline) * 100
            trading_range = row.high - row.low
            body = row.close - row.open
            body_pct = 0.0 if row.open == 0 else (body / row.open) * 100
            upper_wick = max(row.high - max(row.open, row.close), 0.0)
            lower_wick = max(min(row.open, row.close) - row.low, 0.0)
            if body > 1e-12:
                direction: Literal["bullish", "bearish", "neutral"] = "bullish"
            elif body < -1e-12:
                direction = "bearish"
            else:
                direction = "neutral"
            snapshot = ChartCandleSnapshot(
                ts=row.ts,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
                previous_close=baseline,
                change_abs=change_abs,
                change_pct=change_pct,
                trading_range=trading_range,
                body=body,
                body_pct=body_pct,
                upper_wick=upper_wick,
                lower_wick=lower_wick,
                direction=direction,
            )
            detail_snapshots.append(snapshot)
            previous_close_value = row.close

        selected_snapshot = detail_snapshots[selected_index]

        highs = [row.high for row in sorted_rows]
        lows = [row.low for row in sorted_rows]
        total_volume = float(sum(row.volume for row in sorted_rows))
        summary_range = ChartRangeSnapshot(
            first_ts=sorted_rows[0].ts,
            last_ts=sorted_rows[-1].ts,
            high=max(highs),
            low=min(lows),
            total_volume=total_volume,
        )

        overlay_summaries: List[OverlaySeriesSnapshot] = []
        if overlays:
            frame = pd.DataFrame(
                {
                    "ts": [row.ts for row in sorted_rows],
                    "o": [row.open for row in sorted_rows],
                    "h": [row.high for row in sorted_rows],
                    "l": [row.low for row in sorted_rows],
                    "c": [row.close for row in sorted_rows],
                    "v": [row.volume for row in sorted_rows],
                }
            ).set_index("ts")

            # Each overlay leverages the shared indicator helpers to avoid
            # duplicating moving-average logic. The pandas Series aligns with
            # the candle timestamps so the UI can map points 1:1 with rows.
            for overlay in overlays:
                if overlay.kind == "sma":
                    series = simple_moving_average(frame, overlay.window)
                else:
                    series = exponential_moving_average(frame, overlay.window)

                points = tuple(
                    OverlayPointSnapshot(
                        ts=int(ts),
                        value=None if pd.isna(value) else float(value),
                    )
                    for ts, value in series.items()
                )
                # Storing the overlay identifier allows the front-end to toggle
                # visibility without re-requesting the dataset.
                overlay_summaries.append(
                    OverlaySeriesSnapshot(
                        identifier=overlay.identifier,
                        kind=overlay.kind,
                        window=overlay.window,
                        points=points,
                    )
                )

        return ChartArtifactSummary(
            status="ready",
            rows=tuple(sorted_rows),
            range=summary_range,
            selected=selected_snapshot,
            details=tuple(detail_snapshots),
            overlays=tuple(overlay_summaries),
        )


PLAYWRIGHT_REFERENCE_TIME = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)


def _ensure_timezone(value: datetime | None) -> datetime:
    """Normalise *value* to an aware UTC datetime for deterministic fixtures."""
    if value is None:
        return datetime.now(tz=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def default_finance_service(*, now: datetime | None = None) -> FinanceDataService:
    """Return a pre-populated finance service with curated fixtures.

    Parameters
    ----------
    now:
        Reference timestamp injected by the caller. Supplying an explicit value
        allows the E2E environment to freeze the clock while leaving the
        production instance free to rely on the real-time clock.

    """
    reference_time = _ensure_timezone(now)
    quotes = {
        "BTCUSD": QuoteSnapshot(
            price=67120.32,
            change_pct=2.1,
            currency="USD",
            updated_at=reference_time,
        ),
        "AAPL": QuoteSnapshot(
            price=182.63,
            change_pct=-0.4,
            currency="USD",
            updated_at=reference_time,
        ),
        "NVDA": QuoteSnapshot(
            price=905.55,
            change_pct=1.7,
            currency="USD",
            updated_at=reference_time,
        ),
    }
    fundamentals = {
        "AAPL": FundamentalsSnapshot(
            market_cap=2.8e12,
            pe_ratio=28.3,
            dividend_yield=0.005,
            week52_high=199.62,
            week52_low=124.17,
        ),
        "NVDA": FundamentalsSnapshot(
            market_cap=2.2e12,
            pe_ratio=35.5,
            dividend_yield=0.0,
            week52_high=974.0,
            week52_low=350.12,
        ),
        "BTCUSD": FundamentalsSnapshot(
            market_cap=1.3e12,
            pe_ratio=0.0,
            dividend_yield=0.0,
            week52_high=74800.0,
            week52_low=25000.0,
        ),
    }
    news = {
        "NVDA": [
            NewsArticle(
                id="nvda-earnings",
                title="NVIDIA beats expectations as AI demand surges",
                url="https://news.example.com/nvda-earnings",
                published_at=reference_time,
            ),
            NewsArticle(
                id="nvda-gpu",
                title="New GPU architecture targets data centers",
                url="https://news.example.com/nvda-gpu",
                published_at=reference_time.replace(hour=max(0, reference_time.hour - 6)),
            ),
        ],
        "BTCUSD": [
            NewsArticle(
                id="btc-etf",
                title="Spot Bitcoin ETF sees record inflows",
                url="https://news.example.com/btc-etf",
                published_at=reference_time.replace(day=max(1, reference_time.day - 1)),
            )
        ],
    }
    screened = [
        ScreenedAsset(symbol="BTCUSD", sector="Crypto", score=0.92, market_cap=1.3e12),
        ScreenedAsset(symbol="NVDA", sector="Technology", score=0.88, market_cap=2.2e12),
        ScreenedAsset(symbol="AAPL", sector="Technology", score=0.81, market_cap=2.8e12),
    ]
    return FinanceDataService(
        quotes=quotes,
        fundamentals=fundamentals,
        news=news,
        screened_assets=screened,
    )


__all__ = [
    "FinanceDataService",
    "QuoteSnapshot",
    "FundamentalsSnapshot",
    "NewsArticle",
    "ScreenedAsset",
    "ChartCandleSnapshot",
    "ChartArtifactSummary",
    "default_finance_service",
    "PLAYWRIGHT_REFERENCE_TIME",
    "OverlayRequest",
    "OverlaySeriesSnapshot",
    "OverlayPointSnapshot",
]

