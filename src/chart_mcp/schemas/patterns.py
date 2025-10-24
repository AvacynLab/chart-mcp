"""Schemas describing chart pattern detections."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PatternPoint(BaseModel):
    """Point used to describe a detected pattern."""

    ts: int
    price: float


class Pattern(BaseModel):
    """Pattern metadata with confidence score."""

    name: str
    score: float = Field(..., ge=0, le=1)
    start_ts: int
    end_ts: int
    points: List[PatternPoint]
    confidence: float = Field(..., ge=0, le=1)


class PatternsResponse(BaseModel):
    """Wrapper for detected patterns."""

    symbol: str
    timeframe: str
    patterns: List[Pattern]
