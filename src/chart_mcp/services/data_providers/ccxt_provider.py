"""CCXT-backed implementation of the market data provider."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol

import ccxt  # type: ignore[import-untyped]
import pandas as pd

from chart_mcp.config import settings
from chart_mcp.services.data_providers.base import MarketDataProvider
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


def normalize_symbol(symbol: str) -> str:
    """Return a CCXT-friendly pair formatted as ``BASE/QUOTE``.

    The exchanges accept both ``BTCUSDT`` and ``BTC/USDT``. We trim whitespace,
    upper-case the value and inject a slash when the suffix matches a known
    quote currency. Invalid inputs raise :class:`BadRequest` so the HTTP layer
    can surface a consistent ``400`` payload.
    """
    cleaned = symbol.strip().upper()
    if "/" in cleaned:
        return cleaned
    for quote in KNOWN_QUOTES:
        if cleaned.endswith(quote) and len(cleaned) > len(quote):
            base = cleaned[: -len(quote)]
            return f"{base}/{quote}"
    raise BadRequest("Unsupported symbol format")


class CcxtDataProvider(MarketDataProvider):
    """Fetch OHLCV data from exchanges using CCXT."""

    def __init__(self, exchange_id: Optional[str] = None) -> None:
        exchange_name = exchange_id or settings.exchange
        try:
            exchange_class = getattr(ccxt, exchange_name)
        except AttributeError as exc:
            raise UpstreamError(f"Unknown exchange '{exchange_name}'") from exc
        self.client: "_ExchangeLike" = exchange_class({"enableRateLimit": True})

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
        since = start * 1000 if start else None
        timeframe_value = ccxt_timeframe(timeframe)
        attempts = 0
        while True:
            try:
                normalized_symbol = normalize_symbol(symbol)
                raw = self.client.fetch_ohlcv(
                    normalized_symbol,
                    timeframe_value,
                    since=since,
                    limit=limit,
                    params=params,
                )
                break
            except ccxt.RateLimitExceeded as exc:
                attempts += 1
                if attempts > 3:
                    raise UpstreamError("Rate limit exceeded repeatedly") from exc
                time.sleep(1 * attempts)
            except ccxt.BaseError as exc:  # pragma: no cover - network error path
                raise UpstreamError(str(exc)) from exc
        if not raw:
            raise UpstreamError("Empty OHLCV response from exchange")
        frame = pd.DataFrame(raw, columns=["ts", "o", "h", "l", "c", "v"])
        frame["ts"] = frame["ts"].astype(int) // 1000
        if end:
            frame = frame[frame["ts"] <= end]
        frame.sort_values("ts", inplace=True)
        frame.reset_index(drop=True, inplace=True)
        return frame
