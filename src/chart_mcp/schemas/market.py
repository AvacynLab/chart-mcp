"""Pydantic models shared by market data routes and MCP tools."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.common import DatetimeRange
from chart_mcp.utils.timeframes import parse_timeframe


class OhlcvRow(BaseModel):
    """Single OHLCV entry exposed to API consumers."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ts: int = Field(..., description="Unix timestamp in seconds")
    open: float = Field(..., alias="o")
    high: float = Field(..., alias="h")
    low: float = Field(..., alias="l")
    close: float = Field(..., alias="c")
    volume: float = Field(..., alias="v")


class MarketDataRequest(DatetimeRange):
    """Parameters to fetch OHLCV data from a provider."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=20)
    timeframe: str = Field(..., min_length=2, max_length=6)
    limit: int = Field(500, ge=10, le=5000)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return the trading pair uppercased to keep cache keys consistent."""

        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        """Ensure the timeframe matches the supported formats (1m, 1h, 1d, …)."""

        parse_timeframe(value)
        return value


class MarketDataResponse(BaseModel):
    """Normalized OHLCV payload returned by the REST layer."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    symbol: str
    timeframe: str
    source: str
    rows: List[OhlcvRow]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Expose uppercase symbols (``BTC/USDT``)."""

        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        """Return a validated timeframe using the shared parser."""

        parse_timeframe(value)
        return value


class OhlcvQuery(BaseModel):
    """Validated query parameters for the OHLCV REST endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=20, description="Instrument identifier")
    timeframe: str = Field(..., min_length=2, max_length=6, description="Candlestick timeframe")
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

    @field_validator("symbol")
    @classmethod
    def uppercase_query_symbol(cls, value: str) -> str:
        """Return the symbol uppercased to keep cache keys consistent."""

        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def validate_query_timeframe(cls, value: str) -> str:
        """Normalise timeframe strings via :func:`parse_timeframe`."""

        parse_timeframe(value)
        return value


__all__ = [
    "OhlcvRow",
    "MarketDataRequest",
    "MarketDataResponse",
    "OhlcvQuery",
]
