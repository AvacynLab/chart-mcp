"""Regression tests for the tokenised summary streaming helper."""

from __future__ import annotations

from typing import List

from chart_mcp.services.analysis_llm import AnalysisLLMService
from chart_mcp.services.levels import LevelCandidate
from chart_mcp.services.patterns import PatternResult


def _build_level(price: float) -> LevelCandidate:
    """Construct a synthetic support level touching the requested *price*."""
    candidate = LevelCandidate(kind="support", window_start=0, window_end=3, merge_threshold=0.0025)
    for idx, ts in enumerate(range(3)):
        candidate.add_touch(price, ts, idx)
    return candidate


def test_stream_summary_yields_tokens_and_returns_summary() -> None:
    """The generator should yield whitespace-aware tokens then surface the summary."""
    service = AnalysisLLMService()
    levels: List[LevelCandidate] = [_build_level(100.0)]
    patterns = [
        PatternResult(
            name="inverse_head_shoulders",
            score=0.72,
            start_ts=1,
            end_ts=5,
            points=[(1, 99.0)],
            confidence=0.65,
        )
    ]

    generator = service.stream_summary("BTCUSDT", "1h", {"rsi": 55.0}, levels, patterns)
    tokens: List[str] = []
    try:
        while True:
            tokens.append(next(generator))
    except StopIteration as stop:
        summary = stop.value

    assert tokens, "The generator should yield at least one token"
    reconstructed = "".join(tokens).strip()
    assert summary.summary.startswith("Analyse de BTCUSDT"), "Summary should mention the instrument"
    assert reconstructed.startswith("Analyse de BTCUSDT"), "Tokens should reconstruct the summary"
    assert "acheter" not in reconstructed.lower()


def test_stream_summary_preserves_trailing_space_except_last_token() -> None:
    """All tokens except the last one should end with a space for easy concatenation."""
    service = AnalysisLLMService()
    generator = service.stream_summary("ETHUSDT", "15m", {}, [], [])
    emitted: List[str] = []
    try:
        while True:
            emitted.append(next(generator))
    except StopIteration:
        pass

    assert emitted, "Tokens should be generated even for empty inputs"
    for token in emitted[:-1]:
        assert token.endswith(" "), "Intermediate tokens should include trailing spaces"
    assert emitted[-1].strip(), "The last token should contain readable characters"
