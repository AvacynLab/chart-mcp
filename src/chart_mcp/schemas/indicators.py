"""Schemas shared by the indicator computation REST and MCP surfaces.

The models centralise validation so REST, SSE and MCP callers benefit from the
same guardrails when selecting indicator names and parameters."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.services.indicators import (
    CANONICAL_INDICATORS,
    INDICATOR_ALIASES,
    SUPPORTED_INDICATORS,
)


class IndicatorRequest(BaseModel):
    """Body payload to compute an indicator."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=25, description="Trading pair requested for the indicator.")
    timeframe: str = Field(..., min_length=2, max_length=6, description="Timeframe associated with the OHLCV series.")
    indicator: str = Field(..., min_length=2, max_length=48, description="Canonical indicator identifier (ema, rsi...).")
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional numeric parameters forwarded to the indicator implementation.",
    )
    limit: int = Field(500, ge=50, le=2000, description="Maximum number of OHLCV rows to sample from the provider.")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalise symbols to uppercase (``BTC/USDT``)."""
        return value.upper()

    @field_validator("indicator")
    @classmethod
    def normalize_indicator(cls, value: str) -> str:
        """Validate indicator identifiers against the supported set."""
        cleaned = value.strip().lower()
        canonical = INDICATOR_ALIASES.get(cleaned, cleaned)
        if canonical not in CANONICAL_INDICATORS:
            msg = ", ".join(sorted(SUPPORTED_INDICATORS))
            raise ValueError(f"Unsupported indicator '{value}'. Allowed: {msg}")
        return canonical

    @field_validator("params")
    @classmethod
    def cast_param_values(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Ensure JSON numbers are cast to ``float`` for downstream services."""
        return {str(key): float(val) for key, val in value.items()}


class IndicatorValue(BaseModel):
    """Series element for an indicator."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., ge=0, description="Timestamp in seconds associated with the indicator value.")
    values: Dict[str, float] = Field(
        ..., description="Mapping between indicator output labels and their float values."
    )

    @field_validator("values")
    @classmethod
    def coerce_values(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Cast indicator values to floats to avoid Decimal leaks."""
        return {str(key): float(val) for key, val in value.items()}


class IndicatorMeta(BaseModel):
    """Metadata accompanying the computed indicator series."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str = Field(..., min_length=3, max_length=25, description="Symbol used to fetch OHLCV candles.")
    timeframe: str = Field(..., min_length=2, max_length=6, description="Timeframe that generated the candle series.")
    indicator: str = Field(..., min_length=2, max_length=48, description="Canonical indicator identifier.")
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Effective parameter set applied during computation.",
    )

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Expose uppercase symbols."""
        return value.upper()

    @field_validator("indicator")
    @classmethod
    def lowercase_indicator(cls, value: str) -> str:
        """Expose indicator identifiers in lowercase."""
        return value.lower()

    @field_validator("params")
    @classmethod
    def ensure_float_params(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Ensure metadata parameters keep ``float`` semantics."""
        return {str(key): float(val) for key, val in value.items()}


class IndicatorResponse(BaseModel):
    """Response containing computed indicator series."""

    model_config = ConfigDict(extra="forbid")

    series: List[IndicatorValue] = Field(..., description="Chronological indicator datapoints.")
    meta: IndicatorMeta = Field(..., description="Metadata describing the computed series.")


__all__ = [
    "IndicatorRequest",
    "IndicatorValue",
    "IndicatorMeta",
    "IndicatorResponse",
]
