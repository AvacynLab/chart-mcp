"""Unit tests for the streaming schema discriminated union."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chart_mcp.schemas.streaming import (
    DoneStreamPayload,
    ErrorStreamPayload,
    ResultFinalStreamPayload,
    ResultPartialStreamPayload,
    StreamEvent,
    TokenStreamPayload,
    ToolStreamPayload,
)


def test_tool_payload_accepts_optional_fields() -> None:
    """Ensure the tool payload validates optional metadata while enforcing bounds."""
    payload = ToolStreamPayload(
        type="tool",
        payload={
            "tool": "compute_indicator",
            "name": "sma",
            "latest": {"value": 42.0},
            "rows": 12,
        },
    )

    assert payload.type == "tool"
    assert payload.payload.rows == 12
    assert payload.payload.latest == {"value": 42.0}


def test_stream_event_roundtrip_serialises_payload() -> None:
    """The stream event wrapper keeps event names constrained to allowed values."""
    event = StreamEvent(
        event="result_partial",
        data=ResultPartialStreamPayload(
            type="result_partial",
            payload={
                "indicators": {"rsi": {"value": 55.5}},
                "levels": [
                    {"price": 123.4, "kind": "support", "strength": 0.5},
                ],
            },
        ),
    )

    assert event.event == "result_partial"
    assert event.data.payload.levels[0].kind == "support"


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
