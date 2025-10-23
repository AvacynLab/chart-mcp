"""Schemas orchestrating the full analysis pipeline."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from chart_mcp.schemas.levels import Level
from chart_mcp.schemas.patterns import Pattern


class RequestedIndicator(BaseModel):
    """Indicator requested by the client for inclusion in analysis."""

    name: str
    params: Dict[str, float] = Field(default_factory=dict)


class AnalysisRequest(BaseModel):
    """Full analysis request payload."""

    symbol: str
    timeframe: str
    indicators: List[RequestedIndicator] = Field(default_factory=list)
    include_levels: bool = True
    include_patterns: bool = True


class IndicatorSnapshot(BaseModel):
    """Key indicator values summarised for the analysis response."""

    name: str
    latest: Dict[str, float]


class AnalysisResponse(BaseModel):
    """Full analysis output payload."""

    symbol: str
    timeframe: str
    indicators: List[IndicatorSnapshot]
    levels: Optional[List[Level]] = None
    patterns: Optional[List[Pattern]] = None
    summary: str
    disclaimer: str = Field("Analyse à vocation informative uniquement, pas de conseil d'investissement.")
    limits: List[str] = Field(default_factory=list)
