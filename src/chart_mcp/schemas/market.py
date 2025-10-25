"""Schemas dedicated to the market data HTTP endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.common import DatetimeRange


class OhlcvRow(BaseModel):
    """Single OHLCV entry exposed to API consumers."""

    ts: int = Field(..., description="Unix timestamp in seconds")
    open: float = Field(..., alias="o")
    high: float = Field(..., alias="h")
    low: float = Field(..., alias="l")
    close: float = Field(..., alias="c")
    volume: float = Field(..., alias="v")
    model_config = ConfigDict(populate_by_name=True)


class MarketDataRequest(DatetimeRange):
    """Parameters to fetch OHLCV data from a provider."""

    symbol: str = Field(..., min_length=3, max_length=20)
    timeframe: str = Field(..., pattern="^[0-9]+[mhdw]$")
    limit: int = Field(500, ge=10, le=5000)


class MarketDataResponse(BaseModel):
    """Normalized OHLCV payload returned by the REST layer."""

    symbol: str
    timeframe: str
    source: str
    rows: List[OhlcvRow]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize symbol casing for consistent responses."""
        return value.upper()


class OhlcvQuery(BaseModel):
    """Validated query parameters for the OHLCV REST endpoint."""

    symbol: str = Field(..., min_length=3, max_length=20, description="Instrument identifier")
    timeframe: str = Field(
        ...,
        pattern="^[0-9]+[mhdw]$",
        description="Candle duration such as 1m, 1h or 1d",
    )
    limit: int = Field(
        500,
        ge=10,
        le=5000,
        description="Maximum number of candles to retrieve (capped at 5000)",
    )
    start: int | None = Field(
        None,
        ge=0,
        description="Inclusive start timestamp in seconds",
    )
    end: int | None = Field(
        None,
        ge=0,
        description="Inclusive end timestamp in seconds",
    )
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_query_symbol(cls, value: str) -> str:
        """Return the symbol in uppercase to keep cache keys consistent."""
        return value.upper()


__all__ = ["OhlcvRow", "MarketDataRequest", "MarketDataResponse", "OhlcvQuery"]
