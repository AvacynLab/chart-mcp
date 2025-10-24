"""Schemas describing indicator computations."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class IndicatorRequest(BaseModel):
    """Body payload to compute an indicator."""

    symbol: str
    timeframe: str
    indicator: str = Field(..., pattern="^(ema|ma|rsi|macd|bbands)$")
    params: Dict[str, float] = Field(default_factory=dict)
    limit: int = Field(500, ge=50, le=2000)


class IndicatorValue(BaseModel):
    """Series element for an indicator."""

    ts: int
    values: Dict[str, float]


class IndicatorResponse(BaseModel):
    """Response containing computed indicator series."""

    series: List[IndicatorValue]
    meta: Dict[str, float | str]
