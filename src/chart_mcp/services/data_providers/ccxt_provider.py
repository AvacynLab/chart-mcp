"""CCXT data provider implementation."""

from __future__ import annotations

import time
from typing import Optional

import ccxt
import pandas as pd

from chart_mcp.config import settings
from chart_mcp.services.data_providers.base import MarketDataProvider
from chart_mcp.utils.errors import UpstreamError
from chart_mcp.utils.timeframes import ccxt_timeframe


class CcxtDataProvider(MarketDataProvider):
    """Fetch OHLCV data from exchanges using CCXT."""

    def __init__(self, exchange_id: Optional[str] = None) -> None:
        exchange_name = exchange_id or settings.exchange
        try:
            exchange_class = getattr(ccxt, exchange_name)
        except AttributeError as exc:
            raise UpstreamError(f"Unknown exchange '{exchange_name}'") from exc
        self.client = exchange_class({"enableRateLimit": True})

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

        params = {}
        since = start * 1000 if start else None
        timeframe_value = ccxt_timeframe(timeframe)
        attempts = 0
        while True:
            try:
                raw = self.client.fetch_ohlcv(
                    symbol.upper(), timeframe_value, since=since, limit=limit, params=params
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
