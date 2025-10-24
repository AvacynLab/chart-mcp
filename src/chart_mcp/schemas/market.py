"""Schemas for market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, validator

from chart_mcp.schemas.common import DatetimeRange


class OhlcvRow(BaseModel):
    """Single OHLCV entry."""

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
    limit: int = Field(500, ge=10, le=2000)


class MarketDataResponse(BaseModel):
    """Normalized OHLCV payload."""

    symbol: str
    timeframe: str
    source: str
    rows: List[OhlcvRow]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("symbol")
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize symbol casing for consistent responses."""
        return value.upper()
