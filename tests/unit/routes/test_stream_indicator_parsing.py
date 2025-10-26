"""Unit tests for the indicator specification parser used by the stream route."""

from __future__ import annotations

import pytest

from chart_mcp.routes.stream import _parse_indicator_spec
from chart_mcp.utils.errors import BadRequest


class TestParseIndicatorSpec:
    """Verify the robustness of the comma-separated indicator parser."""

    def test_handles_whitespace_and_default_window(self) -> None:
        """Whitespace around the indicator name and parameters is ignored."""

        name, params = _parse_indicator_spec("  EMA : window =  21  ")
        assert name == "ema"
        assert params == {"window": 21.0}

    def test_supports_multiple_key_value_pairs(self) -> None:
        """Key/value parameters are normalised to lowercase float mappings."""

        name, params = _parse_indicator_spec("macd:FAST=12; slow=26 ;Signal=9")
        assert name == "macd"
        assert params == {"fast": 12.0, "slow": 26.0, "signal": 9.0}

    def test_accepts_window_shorthand(self) -> None:
        """Single numeric tokens map to the generic ``window`` parameter."""

        name, params = _parse_indicator_spec("rsi:14")
        assert name == "rsi"
        assert params == {"window": 14.0}

    def test_rejects_unknown_indicators(self) -> None:
        """Unsupported indicators raise a ``BadRequest`` with a helpful message."""

        with pytest.raises(BadRequest, match="Unsupported indicator 'ichimoku'"):
            _parse_indicator_spec("ichimoku:window=9")

    def test_rejects_invalid_parameter_values(self) -> None:
        """Non-numeric parameter values bubble up as ``BadRequest`` errors."""

        with pytest.raises(BadRequest, match="Invalid indicator parameter value"):
            _parse_indicator_spec("ema:window=fast")
