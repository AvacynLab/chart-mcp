"""Schemas representing support/resistance levels returned by the API."""

from __future__ import annotations

from typing import List, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Level(BaseModel):
    """Support or resistance level description."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1, description="Level type (support/resistance)")
    price: float = Field(..., description="Representative price of the level")
    strength: float = Field(..., ge=0.0, le=1.0, description="Confidence score within [0,1]")
    ts_range: Tuple[int, int] = Field(
        ..., description="Tuple describing the inclusive time range of the level"
    )

    @field_validator("ts_range")
    @classmethod
    def ensure_ordered_range(cls, value: Tuple[int, int]) -> Tuple[int, int]:
        """Ensure the range boundaries are chronologically ordered."""
        start, end = value
        if end < start:
            raise ValueError("end timestamp must be greater than or equal to start timestamp")
        return value


class LevelsResponse(BaseModel):
    """Collection of detected levels."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str
    timeframe: str
    levels: List[Level]

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return uppercase symbols so responses remain consistent."""
        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        """Strip whitespace and keep the timeframe lowercase (``1h``)."""
        return value.strip().lower()


__all__ = ["Level", "LevelsResponse"]
