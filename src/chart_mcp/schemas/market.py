"""Pydantic models shared by the market data API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.common import DatetimeRange


class OhlcvRow(BaseModel):
    """Single OHLCV datapoint (timestamps in seconds)."""

    model_config = ConfigDict(extra="forbid")

    ts: int
    o: float
    h: float
    l: float  # noqa: E741 - conventional letter for the low price
    c: float
    v: float

    @property
    def open(self) -> float:
        """Alias for the open price kept for backward compatibility."""
        return self.o

    @property
    def high(self) -> float:
        """Alias for the high price kept for backward compatibility."""
        return self.h

    @property
    def low(self) -> float:
        """Alias for the low price kept for backward compatibility."""
        return self.l

    @property
    def close(self) -> float:
        """Alias for the close price kept for backward compatibility."""
        return self.c

    @property
    def volume(self) -> float:
        """Alias for the volume kept for backward compatibility."""
        return self.v


class MarketDataResponse(BaseModel):
    """Response body returned by the OHLCV endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str
    timeframe: str
    source: str
    rows: List[OhlcvRow]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("symbol", mode="before")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase for downstream caches."""
        return value.upper()


class OhlcvQuery(BaseModel):
    """Query parameters supported by the OHLCV endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=20)
    timeframe: str = Field(..., min_length=2, max_length=6)
    limit: int = Field(500, ge=1, le=5000)
    start: int | None = Field(None, ge=0)
    end: int | None = Field(None, ge=0)
    range: DatetimeRange | None = None

    def resolved_start(self) -> int | None:
        """Return the start timestamp in seconds if a range is provided."""
        if self.start is not None:
            return self.start
        if self.range and self.range.start:
            return int(self.range.start.timestamp())
        return None

    def resolved_end(self) -> int | None:
        """Return the end timestamp in seconds if a range is provided."""
        if self.end is not None:
            return self.end
        if self.range and self.range.end:
            return int(self.range.end.timestamp())
        return None


__all__ = ["OhlcvRow", "MarketDataResponse", "OhlcvQuery"]
