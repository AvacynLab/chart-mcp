"""Schemas describing the Server-Sent Events payloads.

These models are consumed both by the FastAPI streaming route and by the test
suite.  They enforce non-empty textual tokens, non-negative metrics and expose
typed envelopes so frontend and MCP clients receive predictable structures.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

EventType = Literal[
    "tool",
    "token",
    "result_partial",
    "result_final",
    "metric",
    "error",
    "done",
]


ProgressStepStatus = Literal["pending", "in_progress", "completed", "skipped"]


class ProgressStep(BaseModel):
    """Describe the status of a logical pipeline stage for UI progress bars."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    status: ProgressStepStatus
    progress: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fractional completion in [0, 1] for finer-grained loaders.",
    )


class ToolEventDetails(BaseModel):
    """Describe a tool invocation happening within the streaming pipeline."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tool: str = Field(..., min_length=1)
    name: str | None = Field(default=None, min_length=1)
    latest: Dict[str, float] | None = None
    symbol: str | None = Field(default=None, min_length=3, max_length=20)
    timeframe: str | None = Field(default=None, min_length=1)
    rows: int | None = Field(default=None, ge=0)


class ToolStreamPayload(BaseModel):
    """Envelope emitted when a MCP/REST tool starts or finishes."""

    type: Literal["tool"]
    payload: ToolEventDetails


class TokenPayload(BaseModel):
    """Text fragment streamed by the LLM."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)


class TokenStreamPayload(BaseModel):
    """Envelope wrapping incremental textual tokens."""

    type: Literal["token"]
    payload: TokenPayload


class LevelPreview(BaseModel):
    """Compact snapshot of a detected level for partial updates."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1)
    strength: float = Field(..., ge=0.0)
    price: float | None = None


class ResultPartialDetails(BaseModel):
    """Intermediate artefact produced before the final summary."""

    model_config = ConfigDict(extra="forbid")

    levels: List[LevelPreview] = Field(default_factory=list)
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    indicators: Dict[str, Dict[str, float]] | None = None
    steps: List[ProgressStep] = Field(default_factory=list)


class ResultPartialStreamPayload(BaseModel):
    """Envelope used to publish progress and partial artefacts."""

    type: Literal["result_partial"]
    payload: ResultPartialDetails


class LevelDetail(LevelPreview):
    """Full description of a level used in final payloads."""

    ts_range: Tuple[int, int]

    model_config = ConfigDict(extra="forbid")


class PatternDetail(BaseModel):
    """Describe a detected chart pattern with scoring metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0)
    start_ts: int
    end_ts: int
    points: List[Tuple[int, float]] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0)


class ResultFinalDetails(BaseModel):
    """Terminal payload containing the pedagogical AI summary."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., min_length=1)
    levels: List[LevelDetail] = Field(default_factory=list)
    patterns: List[PatternDetail] = Field(default_factory=list)


class ResultFinalStreamPayload(BaseModel):
    """Envelope emitted when the pipeline reaches completion."""

    type: Literal["result_final"]
    payload: ResultFinalDetails


class MetricDetails(BaseModel):
    """Timing metric describing how long a pipeline step took."""

    model_config = ConfigDict(extra="forbid")

    step: str = Field(..., min_length=1)
    ms: float = Field(..., ge=0.0)


class MetricStreamPayload(BaseModel):
    """Envelope used to transport latency measurements."""

    type: Literal["metric"]
    payload: MetricDetails


class ErrorDetails(BaseModel):
    """Structured representation of an error surfaced during streaming."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ErrorStreamPayload(BaseModel):
    """Envelope wrapping an error payload."""

    type: Literal["error"]
    payload: ErrorDetails


class DoneDetails(BaseModel):
    """Terminal marker emitted at the end of the SSE session."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "error"] = Field(default="ok")
    code: str | None = Field(default=None, min_length=1)


class DoneStreamPayload(BaseModel):
    """Envelope signalling the completion of a stream."""

    type: Literal["done"]
    payload: DoneDetails | Dict[str, Any] = Field(default_factory=DoneDetails)

    @model_validator(mode="before")
    @classmethod
    def coerce_payload(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure dictionaries are validated against :class:`DoneDetails`."""
        payload = values.get("payload")
        if isinstance(payload, dict):
            values["payload"] = DoneDetails(**payload)
        return values


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


class StreamEvent(BaseModel):
    """Wrapper representing a full SSE event used by the tests."""

    model_config = ConfigDict(extra="forbid")

    type: EventType
    payload: Dict[str, Any] | StreamPayload


__all__ = [
    "EventType",
    "ToolEventDetails",
    "ToolStreamPayload",
    "TokenPayload",
    "TokenStreamPayload",
    "LevelPreview",
    "ProgressStep",
    "ResultPartialDetails",
    "ResultPartialStreamPayload",
    "LevelDetail",
    "PatternDetail",
    "ResultFinalDetails",
    "ResultFinalStreamPayload",
    "MetricDetails",
    "MetricStreamPayload",
    "ErrorDetails",
    "ErrorStreamPayload",
    "DoneDetails",
    "DoneStreamPayload",
    "StreamPayload",
    "StreamEvent",
    "ProgressStepStatus",
]
