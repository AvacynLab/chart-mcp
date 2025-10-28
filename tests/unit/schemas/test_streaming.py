"""Unit tests for the streaming schema discriminated union."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chart_mcp.schemas.streaming import (
    DoneStreamPayload,
    ErrorStreamPayload,
    HeartbeatStreamPayload,
    ResultFinalStreamPayload,
    ResultPartialStreamPayload,
    StepEndStreamPayload,
    StepStartStreamPayload,
    StreamEvent,
    TokenStreamPayload,
)


def test_step_events_enforce_stage_vocabulary() -> None:
    """Step events should constrain the stage names while accepting metadata."""
    start = StepStartStreamPayload(
        type="step:start",
        payload={
            "stage": "ohlcv",
            "description": "Fetching OHLCV rows",
        },
    )
    end = StepEndStreamPayload(
        type="step:end",
        payload={
            "stage": "ohlcv",
            "elapsed_ms": 12.5,
            "metadata": {"rows": 500},
        },
    )

    assert start.payload.stage == "ohlcv"
    assert end.payload.metadata == {"rows": 500}
    assert end.payload.elapsed_ms == 12.5


def test_heartbeat_payload_requires_timestamp() -> None:
    """Heartbeat events must surface a monotonically increasing timestamp."""
    payload = HeartbeatStreamPayload(type="heartbeat", payload={"ts": 1700000000000})

    assert payload.payload.ts == 1700000000000


def test_stream_event_roundtrip_serialises_payload() -> None:
    """The stream event wrapper keeps event names constrained to allowed values."""
    event = StreamEvent(
        type="result_partial",
        payload={
            "indicators": {"rsi": {"value": 55.5}},
            "levels": [
                {
                    "price": 123.4,
                    "kind": "support",
                    "strength": 0.5,
                    "label": "fort",
                },
            ],
        },
    )

    assert event.type == "result_partial"
    assert event.payload["levels"][0]["kind"] == "support"


def test_done_payload_rejects_unknown_status() -> None:
    """The terminal payload only supports explicit success/error markers."""
    with pytest.raises(ValidationError):
        DoneStreamPayload(type="done", payload={"status": "pending"})


def test_error_payload_requires_non_empty_message() -> None:
    """Error payloads should capture both code and message for observability."""
    with pytest.raises(ValidationError):
        ErrorStreamPayload(type="error", payload={"code": "boom", "message": ""})


def test_token_payload_requires_text() -> None:
    """Token payloads must provide an explicit chunk of text."""
    with pytest.raises(ValidationError):
        TokenStreamPayload(type="token", payload={"text": ""})


def test_result_final_payload_requires_summary() -> None:
    """Final payloads enforce that a summary is present."""
    with pytest.raises(ValidationError):
        ResultFinalStreamPayload(
            type="result_final",
            payload={"summary": "", "levels": [], "patterns": []},
        )


def test_result_partial_rejects_unknown_step_status() -> None:
    """Progress steps only accept the predefined status vocabulary."""
    with pytest.raises(ValidationError):
        ResultPartialStreamPayload(
            type="result_partial",
            payload={
                "levels": [],
                "steps": [{"name": "summary", "status": "unknown"}],
            },
        )


def test_progress_step_rejects_out_of_range_progress() -> None:
    """Progress ratios must remain within the [0, 1] interval."""
    with pytest.raises(ValidationError):
        ResultPartialStreamPayload(
            type="result_partial",
            payload={
                "levels": [],
                "steps": [
                    {
                        "name": "summary",
                        "status": "pending",
                        "progress": 1.5,
                    }
                ],
            },
        )
