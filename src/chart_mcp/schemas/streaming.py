from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from chart_mcp.schemas.market import OhlcvRow

EventType = Literal[
    "heartbeat",
    "ohlcv",
    "range",
    "selected",
    "step:start",
    "step:end",
    "token",
    "indicators",
    "levels",
    "patterns",
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


class HeartbeatDetails(BaseModel):
    """Metadata attached to heartbeat events keeping the SSE channel alive."""

    model_config = ConfigDict(extra="forbid")

    ts: int = Field(..., description="Epoch timestamp in milliseconds when the ping was emitted.")


class HeartbeatStreamPayload(BaseModel):
    """Envelope emitted on a fixed cadence to prevent intermediaries from timing out."""

    type: Literal["heartbeat"]
    payload: HeartbeatDetails


class OhlcvRowPayload(BaseModel):
    """Single OHLCV row streamed to initialise the finance chart."""

    model_config = ConfigDict(extra="forbid")

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_ohlcv(cls, row: OhlcvRow) -> "OhlcvRowPayload":
        """Build a payload from a canonical :class:`~chart_mcp.schemas.market.OhlcvRow`."""
        return cls(ts=row.ts, open=row.o, high=row.h, low=row.l, close=row.c, volume=row.v)


class OhlcvStreamDetails(BaseModel):
    """Bundle the OHLCV series metadata expected by the front-end artifact."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    timeframe: str
    rows: List[OhlcvRowPayload]


class OhlcvStreamPayload(BaseModel):
    """Envelope emitted once the OHLCV dataset is available."""

    type: Literal["ohlcv"]
    payload: OhlcvStreamDetails


class ChartRangePayload(BaseModel):
    """Aggregate boundaries for the rendered window."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    first_ts: int = Field(..., alias="firstTs")
    last_ts: int = Field(..., alias="lastTs")
    high: float
    low: float
    total_volume: float = Field(..., alias="totalVolume")


class RangeStreamPayload(BaseModel):
    """Envelope describing the aggregated OHLCV range."""

    type: Literal["range"]
    payload: ChartRangePayload


class ChartCandlePayload(BaseModel):
    """Detailed analytics for a single candle used by the chart artifact."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    previous_close: float = Field(..., alias="previousClose")
    change_abs: float = Field(..., alias="changeAbs")
    change_pct: float = Field(..., alias="changePct")
    trading_range: float = Field(..., alias="range")
    body: float
    body_pct: float = Field(..., alias="bodyPct")
    upper_wick: float = Field(..., alias="upperWick")
    lower_wick: float = Field(..., alias="lowerWick")
    direction: Literal["bullish", "bearish", "neutral"]


class SelectedStreamPayload(BaseModel):
    """Envelope streaming the currently selected candle and metadata."""

    type: Literal["selected"]
    payload: Dict[str, Any]


class StepEventDetails(BaseModel):
    """Structured description of a pipeline stage lifecycle event."""

    model_config = ConfigDict(extra="forbid")

    stage: Literal["ohlcv", "indicators", "levels", "patterns", "summary"]
    description: str | None = Field(default=None, min_length=1)
    elapsed_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Elapsed processing time for the stage in milliseconds.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form diagnostic payload (e.g. rows fetched, indicator count).",
    )


class StepStartStreamPayload(BaseModel):
    """Envelope published whenever a pipeline stage begins execution."""

    type: Literal["step:start"]
    payload: StepEventDetails


class StepEndStreamPayload(BaseModel):
    """Envelope published when a pipeline stage completes."""

    type: Literal["step:end"]
    payload: StepEventDetails


class TokenPayload(BaseModel):
    """Text fragment streamed by the LLM."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)


class TokenStreamPayload(BaseModel):
    """Envelope wrapping incremental textual tokens."""

    type: Literal["token"]
    payload: TokenPayload


class OverlayPointPayload(BaseModel):
    """Single point composing a streamed overlay series."""

    model_config = ConfigDict(extra="forbid")

    ts: int
    value: float | None


class OverlaySeriesPayload(BaseModel):
    """Overlay series descriptor matching the finance artifact contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    identifier: str = Field(..., alias="id")
    kind: Literal["sma", "ema"] = Field(..., alias="type")
    window: int
    points: List[OverlayPointPayload]


class IndicatorsStreamDetails(BaseModel):
    """Combine overlay descriptors and latest indicator values."""

    model_config = ConfigDict(extra="forbid")

    latest: Dict[str, Dict[str, float]]
    overlays: List[OverlaySeriesPayload]


class IndicatorsStreamPayload(BaseModel):
    """Envelope emitted when indicator computations complete."""

    type: Literal["indicators"]
    payload: IndicatorsStreamDetails


class LevelPreview(BaseModel):
    """Compact snapshot of a detected level for partial updates."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1)
    strength: float = Field(..., ge=0.0)
    label: Literal["fort", "général"]
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


class LevelStreamModel(BaseModel):
    """Level representation streamed to the finance artifact."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    price: float | None
    kind: str
    strength: float
    label: str
    ts_range: Tuple[int, int] = Field(..., alias="tsRange")


class LevelsStreamPayload(BaseModel):
    """Envelope containing the detected support/resistance levels."""

    type: Literal["levels"]
    payload: Dict[str, List[LevelStreamModel]]


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


class PatternStreamModel(BaseModel):
    """Pattern metadata aligned with the finance artifact contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    score: float
    confidence: float
    start_ts: int = Field(..., alias="startTs")
    end_ts: int = Field(..., alias="endTs")
    points: List[Tuple[int, float]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatternsStreamPayload(BaseModel):
    """Envelope containing detected chart patterns."""

    type: Literal["patterns"]
    payload: Dict[str, List[PatternStreamModel]]


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
        HeartbeatStreamPayload,
        OhlcvStreamPayload,
        RangeStreamPayload,
        SelectedStreamPayload,
        StepStartStreamPayload,
        StepEndStreamPayload,
        TokenStreamPayload,
        IndicatorsStreamPayload,
        LevelsStreamPayload,
        PatternsStreamPayload,
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
    "HeartbeatDetails",
    "HeartbeatStreamPayload",
    "OhlcvRowPayload",
    "OhlcvStreamDetails",
    "OhlcvStreamPayload",
    "ChartRangePayload",
    "RangeStreamPayload",
    "ChartCandlePayload",
    "SelectedStreamPayload",
    "StepEventDetails",
    "StepStartStreamPayload",
    "StepEndStreamPayload",
    "TokenPayload",
    "TokenStreamPayload",
    "OverlayPointPayload",
    "OverlaySeriesPayload",
    "IndicatorsStreamDetails",
    "IndicatorsStreamPayload",
    "LevelPreview",
    "ProgressStep",
    "ResultPartialDetails",
    "ResultPartialStreamPayload",
    "LevelStreamModel",
    "LevelsStreamPayload",
    "LevelDetail",
    "PatternDetail",
    "PatternStreamModel",
    "PatternsStreamPayload",
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
