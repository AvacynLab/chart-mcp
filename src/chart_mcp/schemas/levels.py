"""Schemas describing detected support and resistance levels."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class LevelRange(BaseModel):
    """Time range where the level is relevant."""

    start_ts: int
    end_ts: int


class Level(BaseModel):
    """Support or resistance level description."""

    price: float
    strength: float = Field(..., ge=0, le=1)
    kind: str = Field(..., pattern="^(support|resistance)$")
    ts_range: LevelRange


class LevelsResponse(BaseModel):
    """Collection of detected levels."""

    symbol: str
    timeframe: str
    levels: List[Level]
