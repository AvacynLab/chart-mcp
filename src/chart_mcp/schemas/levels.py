"""Schemas describing detected support and resistance levels.

The models enforce strict validation so clients always receive a predictable
shape: timestamps must be ordered, strengths remain bounded within ``[0, 1]``
and symbols are normalised to uppercase.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LevelRange(BaseModel):
    """Time range where the level is relevant."""

    start_ts: int
    end_ts: int
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_bounds(self) -> "LevelRange":
        """Ensure the range boundaries are chronologically ordered."""
        if self.end_ts < self.start_ts:
            msg = "end_ts must be greater than or equal to start_ts"
            raise ValueError(msg)
        return self


class Level(BaseModel):
    """Support or resistance level description."""

    price: float
    strength: float = Field(..., ge=0, le=1)
    kind: str = Field(..., pattern="^(support|resistance)$")
    ts_range: LevelRange
    model_config = ConfigDict(extra="forbid")


class LevelsResponse(BaseModel):
    """Collection of detected levels."""

    symbol: str
    timeframe: str
    levels: List[Level]
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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


__all__ = ["LevelRange", "Level", "LevelsResponse"]
