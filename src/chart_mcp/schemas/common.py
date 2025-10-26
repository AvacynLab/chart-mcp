"""Shared schemas and helpers used across multiple API modules."""

from __future__ import annotations

from datetime import datetime
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from chart_mcp.types import JSONValue
from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES

# Explicit nominal type used whenever a normalized ``BASE/QUOTE`` symbol is
# required.  Using ``NewType`` keeps static typing precise while remaining a
# simple ``str`` at runtime.
SymbolNormalized = NewType("SymbolNormalized", str)


class Symbol(BaseModel):
    """Symbol representation ensuring uppercase formatting."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str = Field(..., min_length=3, max_length=20)

    @field_validator("value")
    @classmethod
    def uppercase(cls, value: str) -> str:
        """Return the symbol uppercased to enforce canonical form."""

        return value.upper()


class Timeframe(BaseModel):
    """Timeframe representation ensuring supported values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str = Field(..., min_length=2, max_length=6)

    @field_validator("value")
    @classmethod
    def validate_supported(cls, value: str) -> str:
        """Ensure the timeframe belongs to the supported set."""

        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"unsupported timeframe '{value}'")
        return value


class DatetimeRange(BaseModel):
    """Datetime range used for OHLCV requests."""

    model_config = ConfigDict(extra="forbid")

    start: datetime | None = None
    end: datetime | None = None

    @field_validator("end")
    @classmethod
    def validate_order(cls, end: datetime | None, info: ValidationInfo) -> datetime | None:
        """Validate that the end timestamp is greater than the start."""

        start = info.data.get("start") if info else None
        if start and end and end <= start:
            raise ValueError("end must be greater than start")
        return end


class ApiError(BaseModel):
    """Schema used by error handlers for JSON responses."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: str
    message: str
    details: JSONValue = Field(default_factory=dict)
    trace_id: str


class Paged(BaseModel):
    """Metadata describing pagination context."""

    model_config = ConfigDict(extra="forbid")

    limit: int
    remaining: int


__all__ = [
    "SymbolNormalized",
    "Symbol",
    "Timeframe",
    "DatetimeRange",
    "ApiError",
    "Paged",
]
