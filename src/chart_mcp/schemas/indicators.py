"""Schemas describing indicator computations.

The REST and MCP layers both share these models so they can advertise a
consistent contract to API consumers.  We normalise user supplied values
early (uppercase symbols, lowercase indicator identifiers) to minimise the
amount of defensive code required in the service layer.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IndicatorRequest(BaseModel):
    """Body payload to compute an indicator."""

    symbol: str
    timeframe: str
    indicator: str
    params: Dict[str, float] = Field(default_factory=dict)
    limit: int = Field(500, ge=50, le=2000)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return the trading pair uppercased to ensure cache consistency."""
        return value.upper()

    @field_validator("indicator", mode="before")
    @classmethod
    def normalize_indicator(cls, value: str) -> str:
        """Accept indicator aliases case-insensitively and validate them."""
        cleaned = str(value).strip().lower()
        allowed = {"ema", "ma", "rsi", "macd", "bbands"}
        if cleaned not in allowed:
            raise ValueError(f"Unsupported indicator '{value}'")
        return cleaned

    @field_validator("params")
    @classmethod
    def cast_param_values(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Cast numeric parameters to ``float`` to avoid JSON number ambiguity."""
        return {key: float(val) for key, val in value.items()}


class IndicatorValue(BaseModel):
    """Series element for an indicator."""

    ts: int
    values: Dict[str, float]
    model_config = ConfigDict(extra="forbid")

    @field_validator("values")
    @classmethod
    def coerce_values(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Ensure indicator series contain float values for serialization."""
        return {key: float(val) for key, val in value.items()}


class IndicatorMeta(BaseModel):
    """Metadata accompanying the computed indicator series."""

    symbol: str
    timeframe: str
    indicator: str
    params: Dict[str, float] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Expose symbols in uppercase ``BASE/QUOTE`` form."""
        return value.upper()

    @field_validator("indicator")
    @classmethod
    def lowercase_indicator(cls, value: str) -> str:
        """Expose indicator identifiers in lowercase."""
        return value.lower()

    @field_validator("params")
    @classmethod
    def ensure_float_params(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Coerce parameters to floats for predictable downstream typing."""
        return {key: float(val) for key, val in value.items()}


class IndicatorResponse(BaseModel):
    """Response containing computed indicator series."""

    series: List[IndicatorValue]
    meta: IndicatorMeta


__all__ = [
    "IndicatorRequest",
    "IndicatorValue",
    "IndicatorMeta",
    "IndicatorResponse",
]
