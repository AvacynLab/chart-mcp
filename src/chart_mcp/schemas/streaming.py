"""Schemas describing streaming event payloads.

These models provide a discriminated union keyed by the ``type`` field so
that streaming artefacts can be validated without resorting to ``Any``.
The schema is intentionally aligned with the SSE payloads emitted by the
``StreamingService`` to keep unit tests and runtime logging consistent.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Tuple, Union

from pydantic import BaseModel, Field


class ToolEventDetails(BaseModel):
    """Describe progress information for long running tooling steps."""

    tool: str = Field(..., min_length=1)
    symbol: str | None = Field(default=None, min_length=1)
    timeframe: str | None = Field(default=None, min_length=1)
    rows: int | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, min_length=1)
    latest: Dict[str, float] | None = None


class ToolStreamPayload(BaseModel):
    """Envelope emitted during tool start/end notifications."""

    type: Literal["tool"]
    payload: ToolEventDetails


class TokenPayload(BaseModel):
    """Text fragment emitted when the LLM streams a sentence."""

    text: str = Field(..., min_length=1)


class TokenStreamPayload(BaseModel):
    """Envelope carrying incremental LLM output."""

    type: Literal["token"]
    payload: TokenPayload


class LevelPreview(BaseModel):
    """Compact representation of a detected support/resistance level."""

    price: float
    kind: str = Field(..., min_length=1)
    strength: float = Field(..., ge=0.0)


class ResultPartialDetails(BaseModel):
    """Intermediate artefact produced once heuristics complete."""

    indicators: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    levels: List[LevelPreview] = Field(default_factory=list)


class ResultPartialStreamPayload(BaseModel):
    """Envelope used for partial aggregation responses."""

    type: Literal["result_partial"]
    payload: ResultPartialDetails


class LevelDetail(LevelPreview):
    """Extended level information exposed in the final summary."""

    ts_range: Tuple[int, int]


class PatternDetail(BaseModel):
    """Final artefact describing a detected chart pattern."""

    name: str = Field(..., min_length=1)
    score: float
    confidence: float = Field(..., ge=0.0)
    start_ts: int
    end_ts: int


class ResultFinalDetails(BaseModel):
    """Terminal payload containing the full AI generated summary."""

    summary: str = Field(..., min_length=1)
    levels: List[LevelDetail] = Field(default_factory=list)
    patterns: List[PatternDetail] = Field(default_factory=list)


class ResultFinalStreamPayload(BaseModel):
    """Envelope emitted once the pipeline completes successfully."""

    type: Literal["result_final"]
    payload: ResultFinalDetails


class MetricDetails(BaseModel):
    """Timing information captured at the end of a pipeline step."""

    step: str = Field(..., min_length=1)
    ms: float = Field(..., ge=0.0)


class MetricStreamPayload(BaseModel):
    """Envelope carrying timing metrics for pipeline diagnostics."""

    type: Literal["metric"]
    payload: MetricDetails


class ErrorDetails(BaseModel):
    """Describe a failure surfaced to the SSE consumer."""

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ErrorStreamPayload(BaseModel):
    """Envelope standardising error reporting in the stream."""

    type: Literal["error"]
    payload: ErrorDetails


class DoneDetails(BaseModel):
    """Signal the terminal status of the streaming pipeline."""

    status: Literal["success", "error"]
    code: str | None = Field(default=None, min_length=1)


class DoneStreamPayload(BaseModel):
    """Envelope ensuring terminal events share a consistent shape."""

    type: Literal["done"]
    payload: DoneDetails


StreamPayload = Annotated[
    Union[
        ToolStreamPayload,
        TokenStreamPayload,
        ResultPartialStreamPayload,
        ResultFinalStreamPayload,
        MetricStreamPayload,
        ErrorStreamPayload,
        DoneStreamPayload,
    ],
    Field(discriminator="type"),
]
"""Discriminated union used by SSE payloads to guarantee typed artefacts."""


EventType = Literal[
    "tool_start",
    "tool_end",
    "tool_log",
    "token",
    "result_partial",
    "result_final",
    "metric",
    "error",
    "done",
]


class StreamEvent(BaseModel):
    """Structured SSE event carrying the type and an arbitrary payload."""

    type: EventType
    payload: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ToolStreamPayload",
    "TokenStreamPayload",
    "ResultPartialStreamPayload",
    "ResultFinalStreamPayload",
    "MetricStreamPayload",
    "ErrorStreamPayload",
    "DoneStreamPayload",
    "StreamPayload",
    "EventType",
    "StreamEvent",
    "MetricDetails",
]
