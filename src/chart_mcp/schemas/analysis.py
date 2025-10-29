"""Schemas orchestrating the full analysis pipeline.

The goal is to make the REST, SSE and MCP outputs structurally identical so
clients can safely consume the data without ad-hoc guards.  Validators enforce
symbol normalisation and ensure summaries remain within the requested bounds.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chart_mcp.schemas.levels import Level
from chart_mcp.schemas.patterns import Pattern


class RequestedIndicator(BaseModel):
    """Indicator requested by the client for inclusion in analysis."""

    name: str = Field(
        ..., min_length=2, max_length=48, description="Indicator identifier (ema, rsi, ...)."
    )
    params: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional parameter mapping forwarded to the indicator service.",
    )
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Normalise indicator names to lowercase."""
        return value.lower()

    @field_validator("params")
    @classmethod
    def cast_params(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Ensure params are floats to simplify downstream serialisation."""
        return {key: float(val) for key, val in value.items()}


class AnalysisRequest(BaseModel):
    """Full analysis request payload."""

    symbol: str = Field(
        ..., min_length=3, max_length=20, description="Symbol to analyse (case-insensitive)."
    )
    timeframe: str = Field(
        ..., min_length=2, max_length=6, description="Timeframe identifier for OHLCV candles."
    )
    indicators: List[RequestedIndicator] = Field(
        default_factory=list,
        description="Optional set of indicators to compute alongside the analysis.",
    )
    include_levels: bool = Field(
        True, description="Request detection of support/resistance levels."
    )
    include_patterns: bool = Field(True, description="Request detection of chart patterns.")
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalise the requested symbol in uppercase."""
        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        """Expose timeframe identifiers in lowercase (``1h``)."""
        return value.lower()


class IndicatorSnapshot(BaseModel):
    """Key indicator values summarised for the analysis response."""

    name: str = Field(
        ..., min_length=2, max_length=48, description="Indicator identifier exposed to clients."
    )
    latest: Dict[str, float] = Field(
        ..., description="Mapping containing the most recent indicator highlights."
    )
    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def lowercase_name(cls, value: str) -> str:
        """Publish indicator names in lowercase for consistency."""
        return value.lower()

    @field_validator("latest")
    @classmethod
    def cast_latest(cls, value: Dict[str, float]) -> Dict[str, float]:
        """Ensure numeric outputs are floats for JSON serialisation."""
        return {key: float(val) for key, val in value.items()}


class AnalysisResponse(BaseModel):
    """Full analysis output payload."""

    symbol: str = Field(
        ..., min_length=3, max_length=20, description="Analysed trading symbol (uppercase)."
    )
    timeframe: str = Field(
        ..., min_length=2, max_length=6, description="Timeframe used to generate the analysis."
    )
    indicators: List[IndicatorSnapshot] = Field(
        ..., description="Indicator highlights surfaced to the client."
    )
    levels: Optional[List[Level]] = Field(
        default=None,
        description="Optional list of detected support and resistance levels.",
    )
    patterns: Optional[List[Pattern]] = Field(
        default=None,
        description="Optional list of detected chart patterns.",
    )
    summary: str = Field(..., max_length=400, description="Token-limited natural language summary.")
    disclaimer: str = Field(
        "Analyse à vocation informative uniquement, pas de conseil d'investissement.",
        description="Regulatory disclaimer appended to every analysis.",
    )
    limits: List[str] = Field(
        default_factory=list,
        description="List of caveats (data gaps, rate limits, etc.) to surface in the UI.",
    )
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Return uppercase symbol for the analysis response."""
        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        """Expose timeframe values in lowercase."""
        return value.lower()

    @field_validator("limits")
    @classmethod
    def strip_limits(cls, value: List[str]) -> List[str]:
        """Remove blank strings to avoid noisy payload entries."""
        return [item.strip() for item in value if item.strip()]


__all__ = [
    "RequestedIndicator",
    "AnalysisRequest",
    "IndicatorSnapshot",
    "AnalysisResponse",
]
