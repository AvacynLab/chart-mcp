from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import pytest

from chart_mcp import mcp_server
from chart_mcp.services.analysis_llm import AnalysisSummary
from chart_mcp.services.search.searxng_client import SearchResult

SNAPSHOT_PATH = Path(__file__).parent.parent / "snapshots" / "mcp_contract.json"


@pytest.fixture(autouse=True)
def stub_mcp_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace heavy services with deterministic doubles for contract tests."""
    frame = pd.DataFrame(
        [
            {"ts": 1, "o": 1.0, "h": 1.2, "l": 0.8, "c": 1.1, "v": 10.0},
            {"ts": 2, "o": 1.1, "h": 1.3, "l": 0.9, "c": 1.2, "v": 12.5},
            {"ts": 3, "o": 1.2, "h": 1.4, "l": 1.0, "c": 1.25, "v": 11.0},
        ]
    )

    class DummyProvider:
        def __init__(self, data: pd.DataFrame) -> None:
            self._data = data

        def get_ohlcv(self, *args, **kwargs) -> pd.DataFrame:  # type: ignore[no-untyped-def]
            return self._data.copy()

    class DummyIndicatorService:
        def compute(self, data: pd.DataFrame, name: str, params: Dict[str, float]) -> pd.DataFrame:
            values = {f"{name}_value": [1.01, 1.02, 1.03]}
            return pd.DataFrame(values, index=data.index)

    class DummyLevel:
        def __init__(self, price: float, strength: float, kind: str, start: int, end: int, label: str) -> None:
            self.price = price
            self.strength = strength
            self.kind = kind
            self._ts_range = (start, end)
            self.strength_label = label

        @property
        def ts_range(self) -> tuple[int, int]:
            return self._ts_range

    class DummyLevelsService:
        def detect_levels(
            self,
            data: pd.DataFrame,
            *,
            max_levels: int = 10,
            distance: int | None = None,
            prominence: float | None = None,
            merge_threshold: float = 0.0025,
            min_touches: int = 2,
        ) -> List[DummyLevel]:
            _ = (distance, prominence, merge_threshold, min_touches)
            return [
                DummyLevel(1.2, 0.72, "resistance", 1, 3, "fort"),
                DummyLevel(0.95, 0.48, "support", 1, 2, "général"),
            ][:max_levels]

    class DummyPattern:
        def __init__(self) -> None:
            self.name = "channel"
            self.score = 0.7
            self.start_ts = 1
            self.end_ts = 3
            self.confidence = 0.6
            self.points = [(1, 1.1), (3, 1.25)]
            self.metadata = {"direction": "neutral"}

    class DummyPatternsService:
        def detect(self, data: pd.DataFrame) -> List[DummyPattern]:
            return [DummyPattern()]

    class DummyAnalysisService:
        def summarize(
            self,
            symbol: str,
            timeframe: str,
            indicator_highlights: Dict[str, float],
            levels: Iterable[DummyLevel],
            patterns: Iterable[DummyPattern],
        ) -> AnalysisSummary:
            _ = (indicator_highlights, list(levels), list(patterns))
            return AnalysisSummary(
                summary=f"Analyse {symbol} {timeframe}",
                disclaimer="Test disclaimer",
            )

    class DummySearchClient:
        def __init__(self) -> None:
            self.calls: List[Dict[str, object]] = []
            self._results = [
                SearchResult(
                    title="BTC weekly outlook",
                    url="https://example.com/btc",
                    snippet="Analyse hebdomadaire",
                    source="crypto-news",
                    score=0.85,
                )
            ]

        def search(
            self,
            *,
            query: str,
            categories: Iterable[str] | None = None,
            time_range: str | None = None,
            language: str = "fr",
        ) -> List[SearchResult]:
            self.calls.append(
                {
                    "query": query,
                    "categories": list(categories or []),
                    "time_range": time_range,
                    "language": language,
                }
            )
            return self._results

    monkeypatch.setattr(mcp_server, "_provider", DummyProvider(frame))
    monkeypatch.setattr(mcp_server, "_indicator_service", DummyIndicatorService())
    monkeypatch.setattr(mcp_server, "_levels_service", DummyLevelsService())
    monkeypatch.setattr(mcp_server, "_patterns_service", DummyPatternsService())
    monkeypatch.setattr(mcp_server, "_analysis_service", DummyAnalysisService())
    monkeypatch.setattr(mcp_server, "_search_client", DummySearchClient())


def load_snapshot() -> Dict[str, object]:
    """Return the stored snapshot for MCP tool payloads."""
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as handler:
        return json.load(handler)


def test_get_crypto_data_matches_snapshot() -> None:
    """OHLCV tool should expose validated payloads."""
    snapshot = load_snapshot()
    records = mcp_server.get_crypto_data("BTCUSDT", "1h", limit=10)
    assert records == snapshot["ohlcv"]


def test_compute_indicator_flattens_values() -> None:
    """Indicator tool must flatten values and match the stored contract."""
    snapshot = load_snapshot()
    records = mcp_server.compute_indicator("BTCUSDT", "1h", indicator="ema")
    assert records == snapshot["indicator"]


def test_levels_tool_injects_strength_label() -> None:
    """Support/resistance tool returns enriched payloads."""
    snapshot = load_snapshot()
    records = mcp_server.identify_support_resistance("BTCUSDT", "1h", params={"max_levels": 1})
    assert records == snapshot["levels"]


def test_patterns_tool_returns_metadata() -> None:
    """Pattern tool includes metadata for downstream rendering."""
    snapshot = load_snapshot()
    records = mcp_server.detect_chart_patterns("BTCUSDT", "1h", params={"min_score": 0.5})
    assert records == snapshot["patterns"]


def test_analysis_tool_accepts_payload_mapping() -> None:
    """Summary tool should parse payload dictionaries and normalise the symbol."""
    snapshot = load_snapshot()
    response = mcp_server.generate_analysis_summary(
        {
            "symbol": "btcusdt",
            "timeframe": "1h",
            "limit": 10,
            "indicators": [{"name": "ema", "params": {"window": 21}}],
            "include_levels": True,
            "include_patterns": True,
        }
    )
    assert response == snapshot["analysis"]


def test_analysis_tool_backward_compat_signature() -> None:
    """Legacy signature (symbol, timeframe) remains supported for CLI users."""
    result = mcp_server.generate_analysis_summary("BTCUSDT", "1h", indicators=[], limit=10)
    assert result["summary"].startswith("Analyse BTC/USDT")
    assert result["disclaimer"] == "Test disclaimer"
