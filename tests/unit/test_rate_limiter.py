"""Unit tests for the in-memory rate limiter primitives."""

from __future__ import annotations

from typing import List

import pytest

from chart_mcp.utils.errors import TooManyRequests
from chart_mcp.utils.ratelimit import RateLimiter


class Clock:
    """Deterministic monotonic clock used to drive limiter windows."""

    def __init__(self) -> None:
        self._history: List[float] = [0.0]

    def advance(self, seconds: float) -> None:
        """Advance the synthetic clock by ``seconds`` to simulate time passing."""
        self._history.append(self._history[-1] + seconds)

    def __call__(self) -> float:
        """Return the current monotonic timestamp for the limiter under test."""
        return self._history[-1]


def test_rate_limiter_allows_burst_within_window() -> None:
    clock = Clock()
    limiter = RateLimiter(3, clock=clock)
    for _ in range(3):
        limiter.acquire("client")


def test_rate_limiter_blocks_when_exceeding_quota() -> None:
    clock = Clock()
    limiter = RateLimiter(2, clock=clock)
    limiter.acquire("client")
    limiter.acquire("client")
    with pytest.raises(TooManyRequests):
        limiter.acquire("client")


def test_rate_limiter_frees_slots_after_window() -> None:
    clock = Clock()
    limiter = RateLimiter(1, clock=clock)
    limiter.acquire("client")
    clock.advance(61.0)
    limiter.acquire("client")


def test_rate_limiter_bypass_allows_unlimited_calls() -> None:
    limiter = RateLimiter(1, bypass=True)
    for _ in range(10):
        limiter.acquire("client")

