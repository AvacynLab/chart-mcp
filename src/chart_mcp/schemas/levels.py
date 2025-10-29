"""Schemas encapsulating support and resistance level outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class LevelRange(BaseModel):
    """Timestamp range delimiting where a level was detected."""

    model_config = ConfigDict(extra="forbid")

    start_ts: int = Field(
        ..., ge=0, description="Inclusive timestamp of the first touch (seconds)."
    )
    end_ts: int = Field(..., ge=0, description="Inclusive timestamp of the last touch (seconds).")


class Level(BaseModel):
    """Support/resistance level representation."""

    model_config = ConfigDict(extra="forbid")

    price: float = Field(..., gt=0.0, description="Price at which the level was detected.")
    strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite strength score normalised between 0 and 1.",
    )
    kind: Literal["support", "resistance"] = Field(
        ..., description="Indicates whether the level acts as support or resistance."
    )
    ts_range: LevelRange = Field(
        ..., description="Timestamp interval covering the touches considered."
    )
    strength_label: Literal["fort", "général"] = Field(
        ..., description="Human-readable label derived from the strength score."
    )


class LevelsResponse(BaseModel):
    """Response payload returned by the levels route."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(
        ..., min_length=3, max_length=20, description="Symbol analysed for the levels detection."
    )
    timeframe: str = Field(
        ..., min_length=2, max_length=6, description="Timeframe used to compute the levels."
    )
    source: str = Field(..., description="Exchange identifier from which candles were fetched.")
    levels: List[Level] = Field(
        ..., description="Detected support/resistance levels sorted by strength."
    )


__all__ = ["LevelRange", "Level", "LevelsResponse"]
