"""Base interface for market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract provider retrieving OHLCV data as pandas DataFrame."""

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return OHLCV data indexed by timestamp."""


__all__ = ["MarketDataProvider"]
