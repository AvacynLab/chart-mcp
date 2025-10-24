"""Reusable pydantic models shared by several endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator

from chart_mcp.types import JSONValue
from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES


class Symbol(BaseModel):
    """Symbol representation ensuring uppercase formatting."""

    value: str = Field(..., min_length=3, max_length=20)

    @validator("value")
    def uppercase(cls, value: str) -> str:
        """Return the symbol uppercased to enforce canonical form."""
        return value.upper()


class Timeframe(BaseModel):
    """Timeframe representation ensuring supported values."""

    value: str = Field(..., pattern="^[0-9]+[mhdw]$")

    @validator("value")
    def validate_supported(cls, value: str) -> str:
        """Ensure the timeframe belongs to the supported set."""
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError("unsupported timeframe")
        return value


class DatetimeRange(BaseModel):
    """Datetime range used for OHLCV requests."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    @validator("end")
    def validate_order(
        cls, end: Optional[datetime], values: Dict[str, Optional[datetime]]
    ) -> Optional[datetime]:
        """Validate that the end timestamp is greater than the start."""
        start = values.get("start")
        if start and end and end <= start:
            raise ValueError("end must be greater than start")
        return end


class ApiError(BaseModel):
    """Schema used by error handlers for JSON responses."""

    code: str
    message: str
    details: JSONValue = Field(default_factory=dict)
    trace_id: str


class Paged(BaseModel):
    """Metadata describing pagination context."""

    limit: int
    remaining: int
