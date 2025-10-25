from __future__ import annotations

import pytest

from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol
from chart_mcp.utils.errors import BadRequest


def test_normalize_symbol_compact_pair() -> None:
    """Compact crypto pairs should be expanded to BASE/QUOTE."""
    assert normalize_symbol("btcusdt") == "BTC/USDT"


def test_normalize_symbol_preserves_slash() -> None:
    """Already normalised symbols remain untouched."""
    assert normalize_symbol("ETH/BTC") == "ETH/BTC"


def test_normalize_symbol_rejects_unknown_quote() -> None:
    """Invalid quotes should raise a ``BadRequest`` to align with API errors."""
    with pytest.raises(BadRequest):
        normalize_symbol("FOOBAR")
