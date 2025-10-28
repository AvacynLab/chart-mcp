"""Unit tests ensuring the CCXT data provider is robust and well normalised."""

from __future__ import annotations

import types
from typing import Any, List, Tuple

import pytest

from chart_mcp.config import settings
from chart_mcp.services.data_providers.ccxt_provider import (
    CcxtDataProvider,
    normalize_symbol,
)
from chart_mcp.utils.errors import BadRequest, UpstreamError
from chart_mcp.utils.timeframes import SUPPORTED_TIMEFRAMES, ccxt_timeframe


class _DummyRateLimit(Exception):
    """Local stand-in for :class:`ccxt.RateLimitExceeded`."""


class _DummyBaseError(Exception):
    """Local stand-in for :class:`ccxt.BaseError`."""


class _RecordingExchange:
    """Exchange double storing calls so assertions stay trivial."""

    id = "test-exchange"

    def __init__(self, ohlcv: List[List[float]]) -> None:
        self.ohlcv = ohlcv
        self.calls: List[Tuple[Any, ...]] = []
        self._fail_once = True

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> List[List[float]]:
        """Return canned OHLCV data while mimicking one rate-limit error."""
        self.calls.append((symbol, timeframe, since, limit, params))
        if self._fail_once:
            self._fail_once = False
            raise _DummyRateLimit("rate limited")
        return self.ohlcv


def _build_ccxt_stub(exchange: _RecordingExchange) -> types.SimpleNamespace:
    """Return a ccxt-like namespace with the provided exchange factory."""

    def _factory(config: dict[str, Any]) -> _RecordingExchange:
        assert config == {"enableRateLimit": True}
        return exchange

    return types.SimpleNamespace(
        binance=_factory,
        RateLimitExceeded=_DummyRateLimit,
        BaseError=_DummyBaseError,
    )


@pytest.mark.parametrize("timeframe", SUPPORTED_TIMEFRAMES)
def test_ccxt_timeframe_accepts_all_supported_values(timeframe: str) -> None:
    """Every declared timeframe must be valid for CCXT mapping."""
    assert ccxt_timeframe(timeframe) == timeframe


def test_normalize_symbol_enforces_known_quotes() -> None:
    """Compact symbols should be expanded to the CCXT ``BASE/QUOTE`` form."""
    assert normalize_symbol("btcusdt") == "BTC/USDT"
    assert normalize_symbol("eth/usdc") == "ETH/USDC"


def test_normalize_symbol_rejects_empty_input() -> None:
    """Empty symbols are rejected so the API returns a 400 error."""
    with pytest.raises(BadRequest):
        normalize_symbol(" ")


def test_get_ohlcv_retries_after_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rate limit exceptions should trigger a retry before succeeding."""
    ohlcv = [
        [1_700_000_000_000, 1.0, 1.5, 0.8, 1.2, 500],
        [1_700_000_060_000, 1.2, 1.7, 1.0, 1.5, 450],
    ]
    exchange = _RecordingExchange(ohlcv)
    stub = _build_ccxt_stub(exchange)
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "chart_mcp.services.data_providers.ccxt_provider.ccxt", stub
    )
    monkeypatch.setattr(
        "chart_mcp.services.data_providers.ccxt_provider.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    provider = CcxtDataProvider()
    frame = provider.get_ohlcv("BTCUSDT", "1H", limit=2)

    assert exchange.calls[0][0] == "BTC/USDT"
    assert exchange.calls[0][1] == "1h"
    assert sleep_calls == [1]
    assert list(frame.columns) == ["ts", "o", "h", "l", "c", "v"]
    assert frame["ts"].tolist() == [1_700_000_000, 1_700_000_060]


def test_get_ohlcv_wraps_ccxt_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic CCXT errors should be surfaced as :class:`UpstreamError`."""
    class _FailingExchange:
        id = "failing-exchange"

        def fetch_ohlcv(self, *args: Any, **kwargs: Any) -> list[list[float]]:
            raise _DummyBaseError("boom")

    stub = types.SimpleNamespace(
        binance=lambda config: _FailingExchange(),
        RateLimitExceeded=_DummyRateLimit,
        BaseError=_DummyBaseError,
    )
    monkeypatch.setattr(
        "chart_mcp.services.data_providers.ccxt_provider.ccxt", stub
    )

    provider = CcxtDataProvider()
    with pytest.raises(UpstreamError):
        provider.get_ohlcv("BTC/USDT", "1m", limit=1)


def test_get_ohlcv_uses_in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated calls with identical parameters should reuse the cached frame."""
    ohlcv = [
        [1_700_000_000_000, 1.0, 1.5, 0.8, 1.2, 500],
        [1_700_000_060_000, 1.2, 1.7, 1.0, 1.5, 450],
    ]
    exchange = _RecordingExchange(ohlcv)
    exchange._fail_once = False
    stub = _build_ccxt_stub(exchange)
    monkeypatch.setattr("chart_mcp.services.data_providers.ccxt_provider.ccxt", stub)
    monkeypatch.setattr(settings, "ohlc_cache_ttl_seconds", 300)
    monkeypatch.setattr(settings, "ohlc_cache_max_entries", 8)

    provider = CcxtDataProvider()
    frame_first = provider.get_ohlcv("BTCUSDT", "1h", limit=2)
    frame_second = provider.get_ohlcv("BTCUSDT", "1h", limit=2)

    assert len(exchange.calls) == 1
    original_open = frame_first.loc[0, "o"]
    frame_second.loc[0, "o"] = 999  # mutate caller copy without affecting cache
    frame_third = provider.get_ohlcv("BTCUSDT", "1h", limit=2)

    assert len(exchange.calls) == 1  # still cached
    assert frame_third.loc[0, "o"] == original_open


def test_get_ohlcv_cache_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired entries should be refetched from the upstream exchange."""
    ohlcv = [[1_700_000_000_000, 1.0, 1.5, 0.8, 1.2, 500]]
    exchange = _RecordingExchange(ohlcv)
    exchange._fail_once = False
    stub = _build_ccxt_stub(exchange)
    monkeypatch.setattr("chart_mcp.services.data_providers.ccxt_provider.ccxt", stub)
    monkeypatch.setattr(settings, "ohlc_cache_ttl_seconds", 30)
    monkeypatch.setattr(settings, "ohlc_cache_max_entries", 4)

    timeline = [0.0]

    def fake_monotonic() -> float:
        return timeline[0]

    monkeypatch.setattr(
        "chart_mcp.services.data_providers.ccxt_provider.time.monotonic",
        fake_monotonic,
    )

    provider = CcxtDataProvider()
    provider.get_ohlcv("BTCUSDT", "1h", limit=1)
    assert len(exchange.calls) == 1

    timeline[0] += 60
    provider.get_ohlcv("BTCUSDT", "1h", limit=1)

    assert len(exchange.calls) == 2


def test_get_ohlcv_cache_respects_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Old entries are evicted once the LRU capacity is reached."""
    ohlcv = [[1_700_000_000_000, 1.0, 1.5, 0.8, 1.2, 500]]
    exchange = _RecordingExchange(ohlcv)
    exchange._fail_once = False
    stub = _build_ccxt_stub(exchange)
    monkeypatch.setattr("chart_mcp.services.data_providers.ccxt_provider.ccxt", stub)
    monkeypatch.setattr(settings, "ohlc_cache_ttl_seconds", 300)
    monkeypatch.setattr(settings, "ohlc_cache_max_entries", 1)

    provider = CcxtDataProvider()
    provider.get_ohlcv("BTCUSDT", "1h", limit=1)
    provider.get_ohlcv("ETHUSDT", "1h", limit=1)

    assert len(exchange.calls) == 2

    provider.get_ohlcv("BTCUSDT", "1h", limit=1)

    assert len(exchange.calls) == 3
