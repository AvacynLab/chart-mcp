"""CCXT-backed implementation of the market data provider."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, Tuple

import ccxt  # type: ignore[import-untyped]
import pandas as pd

from chart_mcp.config import settings
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.services.metrics import metrics
from chart_mcp.utils.errors import BadRequest, UpstreamError
from chart_mcp.utils.timeframes import ccxt_timeframe

if TYPE_CHECKING:

    class _ExchangeLike(Protocol):
        """Structural type describing the ccxt client used at runtime."""

        id: str

        def fetch_ohlcv(
            self,
            symbol: str,
            timeframe: str,
            since: Optional[int] = None,
            limit: Optional[int] = None,
            params: Optional[Dict[str, Any]] = None,
        ) -> list[list[float | int]]: ...


KNOWN_QUOTES: tuple[str, ...] = ("USDT", "USD", "USDC", "BTC", "ETH", "EUR", "GBP")
"""Accepted quote assets used to detect compact symbol inputs."""


CacheKey = Tuple[str, str, int, Optional[int], Optional[int]]
"""Type alias describing how OHLC cache entries are indexed."""


@dataclass
class _CacheEntry:
    """In-memory representation of a cached OHLC response."""

    expires_at: float
    frame: pd.DataFrame


def normalize_symbol(symbol: str) -> str:
    """Return a CCXT-friendly pair formatted as ``BASE/QUOTE`` when possible.

    The exchanges accept both ``BTCUSDT`` and ``BTC/USDT``. We trim whitespace,
    upper-case the value and inject a slash when the suffix matches a known
    quote currency. When no suffix is recognised we return the cleaned symbol
    unchanged so tests and sandbox environments can keep using synthetic
    markets without tripping validation.
    """
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise BadRequest("Symbol cannot be empty")
    if "/" in cleaned:
        return cleaned
    for quote in KNOWN_QUOTES:
        if cleaned.endswith(quote) and len(cleaned) > len(quote):
            base = cleaned[: -len(quote)]
            return f"{base}/{quote}"
    return cleaned


class CcxtDataProvider(MarketDataProvider):
    """Fetch OHLCV data from exchanges using CCXT."""

    def __init__(self, exchange_id: Optional[str] = None) -> None:
        exchange_name = exchange_id or settings.exchange
        try:
            exchange_class = getattr(ccxt, exchange_name)
        except AttributeError as exc:
            raise UpstreamError(f"Unknown exchange '{exchange_name}'") from exc
        self.client: "_ExchangeLike" = exchange_class({"enableRateLimit": True})
        # Cache OHLC payloads keyed by request parameters to avoid hammering
        # the upstream exchange when clients repeatedly query the same window.
        # The simple in-memory LRU works well for the single-process FastAPI
        # deployment target while keeping the implementation trivial to test.
        self._cache: "OrderedDict[CacheKey, _CacheEntry]" = OrderedDict()
        self._cache_lock = Lock()

    def _get_cached_frame(self, key: CacheKey) -> pd.DataFrame | None:
        """Return a cached DataFrame when the entry is still fresh."""
        ttl = settings.ohlc_cache_ttl_seconds
        if ttl <= 0:
            return None
        now = time.monotonic()
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at < now:
                # Drop expired entries eagerly so the cache bounds stay tight.
                del self._cache[key]
                return None
            self._cache.move_to_end(key, last=True)
            return entry.frame.copy(deep=True)

    def _store_in_cache(self, key: CacheKey, frame: pd.DataFrame) -> None:
        """Persist a defensive copy of ``frame`` in the shared cache."""
        ttl = settings.ohlc_cache_ttl_seconds
        if ttl <= 0:
            return
        expires_at = time.monotonic() + ttl
        entry = _CacheEntry(expires_at=expires_at, frame=frame.copy(deep=True))
        with self._cache_lock:
            self._cache[key] = entry
            self._cache.move_to_end(key, last=True)
            max_entries = settings.ohlc_cache_max_entries
            while len(self._cache) > max_entries:
                # Eject the least recently used entry to honour the capacity.
                self._cache.popitem(last=False)

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return OHLCV data as DataFrame with UTC timestamps."""
        params: Dict[str, Any] = {}
        since_ms = start * 1000 if start else None
        timeframe_value = ccxt_timeframe(timeframe)
        normalized_symbol = normalize_symbol(symbol)
        cache_key: CacheKey = (normalized_symbol, timeframe_value, limit, since_ms, end)
        cached_frame = self._get_cached_frame(cache_key)
        if cached_frame is not None:
            return cached_frame
        attempts = 0
        while True:
            try:
                raw = self.client.fetch_ohlcv(
                    normalized_symbol,
                    timeframe_value,
                    since=since_ms,
                    limit=limit,
                    params=params,
                )
                break
            except ccxt.RateLimitExceeded as exc:
                attempts += 1
                if attempts > 3:
                    metrics.record_provider_error("ccxt", self.client.id, "rate_limit")
                    raise UpstreamError("Rate limit exceeded repeatedly") from exc
                time.sleep(1 * attempts)
            except ccxt.BaseError as exc:  # pragma: no cover - network error path
                metrics.record_provider_error("ccxt", self.client.id, exc.__class__.__name__)
                raise UpstreamError(str(exc)) from exc
        if not raw:
            metrics.record_provider_error("ccxt", self.client.id, "empty_response")
            raise UpstreamError("Empty OHLCV response from exchange")
        frame = pd.DataFrame(raw, columns=["ts", "o", "h", "l", "c", "v"])
        frame["ts"] = frame["ts"].astype(int) // 1000
        if end:
            frame = frame[frame["ts"] <= end]
        frame.sort_values("ts", inplace=True)
        frame.reset_index(drop=True, inplace=True)
        self._store_in_cache(cache_key, frame)
        return frame
