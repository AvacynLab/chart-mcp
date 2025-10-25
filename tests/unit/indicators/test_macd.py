"""Tests for MACD indicator computations."""
import pandas as pd
import pytest

from chart_mcp.services.indicators import IndicatorService, macd
from chart_mcp.utils.errors import BadRequest


def test_macd_structure():
    frame = pd.DataFrame({"c": [i for i in range(1, 60)]})
    result = macd(frame, fast=12, slow=26, signal=9)
    assert set(result.columns) == {"macd", "signal", "hist"}


def test_macd_warmup_contains_nan():
    """Initial samples should include NaNs before the signal catches up."""
    frame = pd.DataFrame({"c": list(range(1, 60))})
    result = macd(frame, fast=12, slow=26, signal=9)
    assert result.iloc[:26].isna().any(axis=None)


def test_indicator_service_macd():
    frame = pd.DataFrame({"ts": list(range(60)), "o": [0] * 60, "h": [0] * 60, "l": [0] * 60, "c": list(range(60)), "v": [0] * 60})
    service = IndicatorService()
    data = service.compute(frame, "macd", {})
    assert not data.dropna().empty


def test_macd_parameters_affect_output():
    """Tweaking MACD periods should change the resulting histogram."""
    frame = pd.DataFrame({"c": list(range(1, 120))})
    default = macd(frame)
    slower = macd(frame, fast=20, slow=40, signal=9)
    assert not default.equals(slower)
    assert default["hist"].iloc[-1] != pytest.approx(slower["hist"].iloc[-1])


def test_macd_invalid_parameters():
    """MACD should reject non-positive windows and slow <= fast."""
    frame = pd.DataFrame({"c": list(range(30))})
    with pytest.raises(BadRequest):
        macd(frame, fast=0, slow=10, signal=5)
    with pytest.raises(BadRequest):
        macd(frame, fast=5, slow=5, signal=3)
    with pytest.raises(BadRequest):
        macd(frame, fast=5, slow=10, signal=0)
