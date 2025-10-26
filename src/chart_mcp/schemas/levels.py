"""Schemas for support and resistance routes."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal


class LevelRange(BaseModel):
    """Timestamp range delimiting where a level was detected."""

    model_config = ConfigDict(extra="forbid")

    start_ts: int
    end_ts: int


class Level(BaseModel):
    """Support/resistance level representation."""

    model_config = ConfigDict(extra="forbid")

    price: float
    strength: float
    kind: Literal["support", "resistance"]
    ts_range: LevelRange


class LevelsResponse(BaseModel):
    """Response payload returned by the levels route."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    timeframe: str
    source: str
    """Exchange identifier from which candles were fetched."""
    levels: List[Level]


__all__ = ["LevelRange", "Level", "LevelsResponse"]
