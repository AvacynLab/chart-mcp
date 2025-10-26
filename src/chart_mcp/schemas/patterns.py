"""Schemas representing detected chart patterns."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PatternPoint(BaseModel):
    """Point used to describe a detected pattern."""

    model_config = ConfigDict(extra="forbid")

    ts: int
    price: float


class Pattern(BaseModel):
    """Pattern metadata with confidence score."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)
    start_ts: int
    end_ts: int
    points: List[PatternPoint] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_window(self) -> Pattern:
        """Ensure pattern timestamps are ordered and bounds sensible."""

        if self.end_ts < self.start_ts:
            raise ValueError("end_ts must be greater than or equal to start_ts")
        return self


class PatternsResponse(BaseModel):
    """Wrapper for detected patterns."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str
    timeframe: str
    patterns: List[Pattern]

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return uppercase symbols for downstream consumers."""

        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        """Expose timeframe in lowercase to mirror query expectations."""

        return value.strip().lower()


__all__ = ["PatternPoint", "Pattern", "PatternsResponse"]
