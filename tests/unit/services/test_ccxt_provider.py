"""Unit tests covering the CCXT market data provider adapter."""

from __future__ import annotations

import pandas as pd
import pytest

from chart_mcp.services.data_providers.ccxt_provider import CcxtDataProvider
from chart_mcp.utils.errors import UpstreamError


class DummyClient:
    """Minimal CCXT-like client returning deterministic candles."""

    id = "dummy"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None, int | None]] = []

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None, params=None):
        """Return two synthetic OHLCV rows for testing normalization."""
        self.calls.append((symbol, timeframe, since, limit))
        return [
            [1_000, 1.0, 2.0, 0.5, 1.5, 100],
            [2_000, 1.6, 2.1, 1.2, 1.9, 110],
        ]


def test_ccxt_provider_normalization_and_shape(monkeypatch):
    """Compact symbols should be normalised and timestamps converted to seconds."""

    provider = CcxtDataProvider("binance")
    client = DummyClient()
    provider.client = client

    frame = provider.get_ohlcv("BTCUSDT", "1h", limit=2)

    assert isinstance(frame, pd.DataFrame)

    # Ensure the adapter requested data using the slash formatted symbol and
    # the timeframe mapping expected by ccxt.
    assert client.calls == [("BTC/USDT", "1h", None, 2)]

    # The resulting dataframe keeps the canonical OHLCV column order and sorts
    # rows by timestamp expressed in **seconds** (ccxt uses milliseconds).
    assert list(frame.columns) == ["ts", "o", "h", "l", "c", "v"]
    assert frame["ts"].tolist() == [1, 2]
    assert frame["c"].tolist() == [1.5, 1.9]


def test_ccxt_provider_honours_end_parameter(monkeypatch):
    """Rows strictly greater than the optional ``end`` parameter are filtered out."""

    provider = CcxtDataProvider("binance")
    client = DummyClient()
    provider.client = client

    frame = provider.get_ohlcv("BTCUSDT", "1h", limit=10, end=1)

    assert frame["ts"].tolist() == [1]


def test_ccxt_provider_empty(monkeypatch):
    """An empty upstream payload should surface a dedicated ``UpstreamError``."""

    class EmptyClient(DummyClient):
        def fetch_ohlcv(self, *args, **kwargs):
            return []

    provider = CcxtDataProvider("binance")
    provider.client = EmptyClient()

    with pytest.raises(UpstreamError):
        provider.get_ohlcv("BTC/USDT", "1h", limit=2)
