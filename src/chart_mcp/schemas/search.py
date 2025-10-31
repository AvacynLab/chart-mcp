"""Pydantic models dedicated to the SearxNG-backed search endpoint."""

from __future__ import annotations

from typing import List

from pydantic import AnyHttpUrl, BaseModel, Field


class SearchResult(BaseModel):
    """Single search hit returned by the SearxNG proxy endpoint."""

    title: str = Field(..., description="Result title as provided by the upstream engine.")
    url: AnyHttpUrl = Field(..., description="Canonical URL pointing to the resource.")
    snippet: str = Field(..., description="Short text excerpt describing the result.")
    source: str = Field(..., description="Name of the engine that produced the result.")
    score: float = Field(..., ge=0.0, description="Relative ranking score assigned by SearxNG.")


class SearchResponse(BaseModel):
    """Envelope returned by ``GET /api/v1/search``."""

    query: str = Field(..., description="Original user query forwarded to SearxNG.")
    categories: List[str] = Field(
        default_factory=list, description="Categories applied to the upstream search request."
    )
    time_range: str | None = Field(
        default=None,
        description="Filtre temporel passé à SearxNG (ex. day/week/month) ou ``None`` si absent.",
    )
    results: List[SearchResult] = Field(default_factory=list, description="List of search hits.")
