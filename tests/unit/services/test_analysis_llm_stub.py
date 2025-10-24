"""Tests for analysis summary stub."""

from __future__ import annotations

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult


def test_summary_contains_disclaimer_elements():
    service = AnalysisLLMService()
    levels = [LevelCandidate(price=100, timestamps=[1, 2, 3], kind="support")]
    patterns = [PatternResult(name="triangle", score=0.7, start_ts=1, end_ts=5, points=[(1, 100.0)], confidence=0.6)]
    summary = service.summarize("BTCUSDT", "1h", {"rsi": 55.0}, levels, patterns)
    assert "BTCUSDT" in summary
    assert "support" in summary
    assert "triangle" in summary
    assert "acheter" not in summary.lower()
