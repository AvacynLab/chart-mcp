"""Schemas describing chart pattern detections.

These Pydantic models keep the streaming, REST and MCP contracts aligned by
enforcing bounds on confidence/score and by normalising simple string fields.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PatternPoint(BaseModel):
    """Point used to describe a detected pattern."""

    ts: int
    price: float
    model_config = ConfigDict(extra="forbid")


class Pattern(BaseModel):
    """Pattern metadata with confidence score."""

    name: str
    score: float = Field(..., ge=0, le=1)
    start_ts: int
    end_ts: int
    points: List[PatternPoint]
    confidence: float = Field(..., ge=0, le=1)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_window(self) -> "Pattern":
        """Ensure pattern timestamps are ordered and bounds sensible."""
        if self.end_ts < self.start_ts:
            msg = "end_ts must be greater than or equal to start_ts"
            raise ValueError(msg)
        return self


class PatternsResponse(BaseModel):
    """Wrapper for detected patterns."""

    symbol: str
    timeframe: str
    patterns: List[Pattern]
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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
