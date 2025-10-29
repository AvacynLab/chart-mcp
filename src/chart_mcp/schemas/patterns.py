"""Schemas modelling chart pattern detection outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class PatternPoint(BaseModel):
    """Point composing a detected pattern."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., ge=0, description="Timestamp in seconds corresponding to the point.")
    price: float = Field(..., gt=0.0, description="Price observed at the timestamp.")


class Pattern(BaseModel):
    """Detected pattern with scoring metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Pattern identifier (head_and_shoulders, channel, ...).",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative score expressing how well the detected structure matches the heuristic.",
    )
    start_ts: int = Field(
        ..., ge=0, description="Timestamp of the first candle included in the pattern."
    )
    end_ts: int = Field(
        ..., ge=0, description="Timestamp of the last candle included in the pattern."
    )
    points: List[PatternPoint] = Field(
        ..., description="Key points outlining the detected structure."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score derived from confirmation signals (0-1).",
    )


class PatternsResponse(BaseModel):
    """Response payload returned by the patterns route."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(
        ..., min_length=3, max_length=20, description="Symbol analysed for pattern detection."
    )
    timeframe: str = Field(
        ..., min_length=2, max_length=6, description="Timeframe used for the source candles."
    )
    source: str = Field(
        ..., description="Exchange identifier where the analysed candles originated."
    )
    patterns: List[Pattern] = Field(
        ..., description="Detected patterns sorted by confidence and score."
    )


__all__ = ["PatternPoint", "Pattern", "PatternsResponse"]
