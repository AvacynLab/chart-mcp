"""Pydantic models shared by the market data API endpoints (OHLCV)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.common import DatetimeRange


class OhlcvRow(BaseModel):
    """Single OHLCV datapoint (timestamps in seconds)."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., ge=0, description="Candle open timestamp expressed in seconds since epoch.")
    o: float = Field(..., description="Opening price for the candle.")
    h: float = Field(..., description="Highest traded price during the candle.")
    l: float = Field(..., description="Lowest traded price during the candle.")  # noqa: E741
    c: float = Field(..., description="Closing price for the candle.")
    v: float = Field(..., ge=0.0, description="Total traded volume over the candle period.")

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

    symbol: str = Field(..., min_length=3, max_length=20, description="Symbol requested by the client (uppercase).")
    timeframe: str = Field(..., min_length=2, max_length=6, description="Timeframe used to aggregate the candles.")
    source: str = Field(..., description="Identifier of the upstream exchange or market data provider.")
    rows: List[OhlcvRow] = Field(..., description="Chronologically ordered candle records.")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp indicating when the snapshot was retrieved.",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase for downstream caches."""
        return value.upper()


class OhlcvQuery(BaseModel):
    """Query parameters supported by the OHLCV endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=20, description="Symbol requested (case-insensitive).")
    timeframe: str = Field(..., min_length=2, max_length=6, description="Timeframe identifier such as 1m/1h/1d.")
    limit: int = Field(500, ge=1, le=5000, description="Maximum number of candles to retrieve.")
    start: int | None = Field(None, ge=0, description="Optional inclusive start timestamp (seconds).")
    end: int | None = Field(None, ge=0, description="Optional exclusive end timestamp (seconds).")
    range: DatetimeRange | None = Field(
        None,
        description="Optional datetime range alternative to numeric start/end parameters.",
    )

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
