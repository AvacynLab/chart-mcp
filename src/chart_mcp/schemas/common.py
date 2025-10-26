"""Common helper schemas shared across endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from chart_mcp.types import JSONValue
from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES

SymbolNormalized = NewType("SymbolNormalized", str)


class Symbol(BaseModel):
    """Wrapper ensuring symbols are normalized to uppercase."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    value: str = Field(..., min_length=3, max_length=20)

    @field_validator("value", mode="before")
    @classmethod
    def uppercase(cls, value: str) -> str:
        """Return uppercase symbol string."""
        return value.upper()


class Timeframe(BaseModel):
    """Wrapper enforcing timeframe membership in the supported set."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    value: str = Field(..., min_length=2, max_length=6)

    @field_validator("value", mode="before")
    @classmethod
    def validate_supported(cls, value: str) -> str:
        """Ensure the timeframe is part of the supported list."""
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"unsupported timeframe '{value}'")
        return value


class DatetimeRange(BaseModel):
    """Datetime interval used by multiple query payloads."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    start: datetime | None = None
    end: datetime | None = None

    @field_validator("end", mode="before")
    @classmethod
    def validate_order(cls, value: datetime | None, info: ValidationInfo) -> datetime | None:
        """Ensure the end timestamp is greater than the start timestamp."""
        start = info.data.get("start") if info else None
        if start and value and value <= start:
            raise ValueError("end must be greater than start")
        return value


class ApiErrorPayload(BaseModel):
    """Standard error payload returned by exception handlers."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: str
    message: str
    details: JSONValue = Field(default_factory=dict)
    trace_id: str


class Paged(BaseModel):
    """Pagination metadata."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    limit: int
    remaining: int


__all__ = [
    "SymbolNormalized",
    "Symbol",
    "Timeframe",
    "DatetimeRange",
    "ApiErrorPayload",
    "Paged",
]
