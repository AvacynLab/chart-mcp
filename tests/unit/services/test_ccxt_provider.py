"""Tests for CCXT data provider."""

from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.utils.errors import UpstreamError


class DummyClient:
    """Minimal CCXT-like client returning deterministic candles."""

    id = "dummy"

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None, params=None):
        """Return two synthetic OHLCV rows for testing normalization."""
        return [
            [1000, 1.0, 2.0, 0.5, 1.5, 100],
            [2000, 1.6, 2.1, 1.2, 1.9, 110],
        ]


def test_ccxt_provider_normalization(monkeypatch):
    provider = CcxtDataProvider("binance")
    provider.client = DummyClient()
    frame = provider.get_ohlcv("BTC/USDT", "1h", limit=2)
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == ["ts", "o", "h", "l", "c", "v"]
    assert frame.iloc[0]["ts"] == 1


def test_ccxt_provider_empty(monkeypatch):
    class EmptyClient(DummyClient):
        def fetch_ohlcv(self, *args, **kwargs):
            return []

    provider = CcxtDataProvider("binance")
    provider.client = EmptyClient()
    with pytest.raises(UpstreamError):
        provider.get_ohlcv("BTC/USDT", "1h", limit=2)
