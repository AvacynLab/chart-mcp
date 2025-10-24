"""Schemas describing streaming events payloads."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """Generic NDJSON payload streaming to the client."""

    type: str = Field(..., pattern="^(tool_start|tool_end|tool_log|token|result_partial|result_final|metric|error|done)$")
    payload: Dict[str, Any] = Field(default_factory=dict)
