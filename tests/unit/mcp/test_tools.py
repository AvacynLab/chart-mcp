from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp import mcp_server
from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult


@pytest.fixture(autouse=True)
def stub_mcp_services(monkeypatch):
    """Replace MCP dependencies with deterministic stubs for JSON contract tests."""
    frame = pd.DataFrame(
        [
            {"ts": 1, "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10.0},
            {"ts": 2, "o": 1.6, "h": 2.2, "l": 1.4, "c": 2.0, "v": 12.0},
            {"ts": 3, "o": 2.1, "h": 2.5, "l": 1.9, "c": 2.3, "v": 9.0},
        ]
    )

    class DummyProvider:
        def __init__(self, data: pd.DataFrame) -> None:
            self._data = data

        def get_ohlcv(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self._data.copy()

    class DummyIndicatorService:
        def compute(self, data: pd.DataFrame, name: str, params: dict) -> pd.DataFrame:
            values = pd.DataFrame({f"{name}_value": [1.1, 1.2, 1.3]}, index=data.index)
            return values

    class DummyLevelsService:
        def detect_levels(self, data: pd.DataFrame, *, max_levels: int = 10):
            level = LevelCandidate(price=2.0, timestamps=[1, 2, 3], kind="resistance")
            return [level]

    class DummyPatternsService:
        def detect(self, data: pd.DataFrame):
            result = PatternResult(
                name="channel",
                score=0.7,
                start_ts=1,
                end_ts=3,
                points=[(1, 1.5), (3, 2.5)],
                confidence=0.6,
            )
            return [result]

    monkeypatch.setattr(mcp_server, "_provider", DummyProvider(frame))
    monkeypatch.setattr(mcp_server, "_indicator_service", DummyIndicatorService())
    monkeypatch.setattr(mcp_server, "_levels_service", DummyLevelsService())
    monkeypatch.setattr(mcp_server, "_patterns_service", DummyPatternsService())


def test_get_crypto_data_returns_json_records():
    """OHLCV tool should expose a JSON friendly list of records."""
    records = mcp_server.get_crypto_data("BTCUSDT", "1h", limit=3)

    assert all(isinstance(row["ts"], int) for row in records)
    assert {"o", "h", "l", "c", "v"}.issubset(records[0].keys())


def test_compute_indicator_returns_timestamps_and_values():
    """Indicator computation should align timestamps with floating values."""
    result = mcp_server.compute_indicator("BTCUSDT", "1h", indicator="ema")

    assert result[0]["ts"] == 1
    assert result[-1]["ema_value"] == pytest.approx(1.3)


def test_identify_support_resistance_json_contract():
    """Levels tool must expose numeric fields and a dict range."""
    levels = mcp_server.identify_support_resistance("BTCUSDT", "1h")

    assert levels[0]["ts_range"] == {"start_ts": 1, "end_ts": 3}
    assert levels[0]["kind"] == "resistance"


def test_detect_chart_patterns_serialises_points():
    """Pattern tool should emit points as JSON objects."""
    patterns = mcp_server.detect_chart_patterns("BTCUSDT", "1h")

    assert patterns[0]["points"] == [
        {"ts": 1, "price": 1.5},
        {"ts": 3, "price": 2.5},
    ]
