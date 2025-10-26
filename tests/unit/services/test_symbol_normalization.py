from __future__ import annotations

from chart_mcp.services.data_providers.ccxt_provider import normalize_symbol


def test_normalize_symbol_compact_pair() -> None:
    """Compact crypto pairs should be expanded to BASE/QUOTE."""
    assert normalize_symbol("btcusdt") == "BTC/USDT"


def test_normalize_symbol_preserves_slash() -> None:
    """Already normalised symbols remain untouched."""
    assert normalize_symbol("ETH/BTC") == "ETH/BTC"


def test_normalize_symbol_falls_back_to_cleaned_symbol() -> None:
    """Unrecognised suffixes should return the cleaned symbol unchanged."""
    assert normalize_symbol("FOOBAR") == "FOOBAR"
