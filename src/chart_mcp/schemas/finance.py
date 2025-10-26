"""Pydantic models shared by finance-related REST endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.market import OhlcvQuery, OhlcvRow


class QuoteQuery(BaseModel):
    """Query parameters accepted by the quote endpoint."""

    symbol: str = Field(..., min_length=2, max_length=20, description="Ticker to retrieve")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize the ticker to uppercase for cache stability."""
        return value.upper()


class QuoteResponse(BaseModel):
    """Response body describing a quote snapshot."""

    symbol: str
    price: float
    change_pct: float = Field(..., alias="changePct")
    currency: str
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class FundamentalsQuery(BaseModel):
    """Query parameters for the fundamentals endpoint."""

    symbol: str = Field(..., min_length=2, max_length=20)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return *value* uppercased so fundamentals lookups stay consistent."""
        return value.upper()


class FundamentalsResponse(BaseModel):
    """Response body with core fundamental metrics."""

    symbol: str
    market_cap: float = Field(..., alias="marketCap")
    pe_ratio: float = Field(..., alias="peRatio")
    dividend_yield: float = Field(..., alias="dividendYield")
    week52_high: float = Field(..., alias="week52High")
    week52_low: float = Field(..., alias="week52Low")

    model_config = ConfigDict(populate_by_name=True)


class NewsQuery(BaseModel):
    """Query parameters accepted by the news endpoint."""

    symbol: str = Field(..., min_length=2, max_length=20)
    # Limit the page size to keep deterministic fixture sets manageable during tests.
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of articles to fetch per page",
    )
    offset: int = Field(0, ge=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return *value* uppercased to match the stored news snapshots."""
        return value.upper()


class NewsItemModel(BaseModel):
    """Serialized representation of a news article."""

    id: str
    title: str
    url: str
    published_at: datetime = Field(..., alias="publishedAt")

    model_config = ConfigDict(populate_by_name=True)


class NewsResponse(BaseModel):
    """Response body containing news for a symbol."""

    symbol: str
    items: list[NewsItemModel]

    model_config = ConfigDict(populate_by_name=True)


class ScreenQuery(BaseModel):
    """Query parameters for the screener endpoint."""

    sector: str | None = Field(
        None,
        max_length=40,
        description="Optional sector filter (kept short to avoid noisy queries)",
    )
    min_score: float = Field(
        0.0,
        alias="minScore",
        ge=0.0,
        le=1.0,
        description="Minimum quality score required to keep a result",
    )
    # Cap the screener page size to avoid returning excessive rows during UI tests.
    limit: int = Field(20, ge=1, le=100, description="Maximum number of screener results")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)


class ScreenedAssetModel(BaseModel):
    """Serialized screener result."""

    symbol: str
    sector: str
    score: float
    market_cap: float = Field(..., alias="marketCap")

    model_config = ConfigDict(populate_by_name=True)


class ScreenResponse(BaseModel):
    """Response body returned by the screener endpoint."""

    results: list[ScreenedAssetModel]

    model_config = ConfigDict(populate_by_name=True)


class ChartArtifactQuery(OhlcvQuery):
    """Query parameters for the finance chart artifact endpoint."""

    selected_ts: int | None = Field(
        None,
        alias="selectedTs",
        ge=0,
        description="Optional timestamp to highlight within the returned candles",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class ChartRangeModel(BaseModel):
    """Aggregated boundaries and totals for a batch of candles."""

    first_ts: int = Field(..., alias="firstTs")
    last_ts: int = Field(..., alias="lastTs")
    high: float
    low: float
    total_volume: float = Field(..., alias="totalVolume")

    model_config = ConfigDict(populate_by_name=True)


class ChartCandleDetails(BaseModel):
    """Detailed information about the currently selected candle.

    The schema intentionally mirrors :class:`ChartCandleSnapshot` so the API can
    expose trading-friendly analytics (body/wick/price range) without requiring
    the UI to recompute them.
    """

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    previous_close: float = Field(..., alias="previousClose")
    change_abs: float = Field(..., alias="changeAbs")
    change_pct: float = Field(..., alias="changePct")
    trading_range: float = Field(..., alias="range")
    body: float
    body_pct: float = Field(..., alias="bodyPct")
    upper_wick: float = Field(..., alias="upperWick")
    lower_wick: float = Field(..., alias="lowerWick")
    direction: Literal["bullish", "bearish", "neutral"]

    model_config = ConfigDict(populate_by_name=True)


class ChartArtifactResponse(BaseModel):
    """Structured payload consumed by the finance chart artifact UI."""

    status: Literal["empty", "ready"]
    symbol: str
    timeframe: str
    rows: list[OhlcvRow]
    range: ChartRangeModel | None
    selected: ChartCandleDetails | None
    details: list[ChartCandleDetails]
    overlays: list["OverlaySeriesModel"]

    model_config = ConfigDict(populate_by_name=True)


class ChartOverlayToggle(BaseModel):
    """Overlay descriptor accepted by the chart artefact query."""

    id: str = Field(..., min_length=1, max_length=40)
    type: Literal["sma", "ema"]
    window: int = Field(..., ge=2, le=500, description="Window length for the overlay")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class OverlayPointModel(BaseModel):
    """Single point composing an overlay series."""

    ts: int
    value: float | None

    model_config = ConfigDict(populate_by_name=True)


class OverlaySeriesModel(BaseModel):
    """Overlay series returned alongside the chart artefact."""

    id: str
    type: Literal["sma", "ema"]
    window: int
    points: list[OverlayPointModel]

    model_config = ConfigDict(populate_by_name=True)


__all__ = [
    "QuoteQuery",
    "QuoteResponse",
    "FundamentalsQuery",
    "FundamentalsResponse",
    "NewsQuery",
    "NewsItemModel",
    "NewsResponse",
    "ScreenQuery",
    "ScreenedAssetModel",
    "ScreenResponse",
    "ChartArtifactQuery",
    "ChartRangeModel",
    "ChartCandleDetails",
    "ChartArtifactResponse",
    "ChartOverlayToggle",
    "OverlaySeriesModel",
    "OverlayPointModel",
]
