"""Tests for analysis summary stub."""

from __future__ import annotations

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult


def test_summary_contains_disclaimer_elements():
    service = AnalysisLLMService()
    level = LevelCandidate(kind="support", window_start=0, window_end=10, merge_threshold=0.0025)
    for idx, ts in enumerate([1, 2, 3]):
        level.add_touch(100.0, ts, idx)
    levels = [level]
    patterns = [
        PatternResult(
            name="triangle", score=0.7, start_ts=1, end_ts=5, points=[(1, 100.0)], confidence=0.6
        )
    ]
    result = service.summarize("BTCUSDT", "1h", {"rsi": 55.0}, levels, patterns)
    summary = result.summary
    assert "BTCUSDT" in summary
    assert "support" in summary
    assert "triangle" in summary
    assert "acheter" not in summary.lower()
    assert result.disclaimer == service.disclaimer


def test_summary_truncated_below_limit_and_neutral():
    service = AnalysisLLMService()
    long_indicators = {f"ema_{idx}": float(idx) for idx in range(50)}
    result = service.summarize("ETHUSDT", "15m", long_indicators, [], [])
    summary = result.summary
    assert len(summary) <= 400
    lowered = summary.lower()
    for forbidden in {"acheter", "vendre", "buy", "sell"}:
        assert forbidden not in lowered
