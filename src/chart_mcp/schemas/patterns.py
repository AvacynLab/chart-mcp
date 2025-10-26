"""Schemas for chart pattern detection routes."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict


class PatternPoint(BaseModel):
    """Point composing a detected pattern."""

    model_config = ConfigDict(extra="forbid")

    ts: int
    price: float


class Pattern(BaseModel):
    """Detected pattern with scoring metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str
    score: float
    start_ts: int
    end_ts: int
    points: List[PatternPoint]
    confidence: float


class PatternsResponse(BaseModel):
    """Response payload returned by the patterns route."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    timeframe: str
    source: str
    """Exchange identifier where the analysed candles originated."""
    patterns: List[Pattern]


__all__ = ["PatternPoint", "Pattern", "PatternsResponse"]
