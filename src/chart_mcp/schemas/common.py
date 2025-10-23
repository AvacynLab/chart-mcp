"""Common pydantic schemas shared across routes and tools."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator

from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES


class Symbol(BaseModel):
    """Symbol representation ensuring uppercase formatting."""

    value: str = Field(..., min_length=3, max_length=20)

    @validator("value")
    def uppercase(cls, value: str) -> str:
        return value.upper()


class Timeframe(BaseModel):
    """Timeframe representation ensuring supported values."""

    value: str = Field(..., pattern="^[0-9]+[mhdw]$")

    @validator("value")
    def validate_supported(cls, value: str) -> str:
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError("unsupported timeframe")
        return value


class DatetimeRange(BaseModel):
    """Datetime range used for OHLCV requests."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    @validator("end")
    def validate_order(cls, end: Optional[datetime], values):
        start = values.get("start")
        if start and end and end <= start:
            raise ValueError("end must be greater than start")
        return end


class ApiError(BaseModel):
    """Schema used by error handlers for JSON responses."""

    code: str
    message: str
    details: dict = Field(default_factory=dict)
    trace_id: str


class Paged(BaseModel):
    """Metadata describing pagination context."""

    limit: int
    remaining: int
