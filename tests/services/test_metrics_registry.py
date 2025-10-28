"""Unit tests for the metrics registry helper."""

from __future__ import annotations

from chart_mcp.services.metrics import MetricsRegistry


def test_metrics_registry_records_observations() -> None:
    """Counters and histograms should register increments and observations."""
    registry = MetricsRegistry()
    registry.record_provider_error("ccxt", "kraken", "rate_limit")
    registry.observe_stage_duration("summary", 0.5)
    registry.increment_stream_event("token")
    snapshot = registry.render().decode()
    assert "provider_errors_total" in snapshot
    assert "ccxt" in snapshot and "kraken" in snapshot
    assert "stream_stage_duration_seconds_sum" in snapshot
    assert "stream_events_total" in snapshot and "token" in snapshot


def test_metrics_registry_reset_resets_counters() -> None:
    """Calling reset should clear previous values from the registry."""
    registry = MetricsRegistry()
    registry.record_provider_error("ccxt", "binance", "timeout")
    assert "timeout" in registry.render().decode()
    registry.reset()
    snapshot = registry.render().decode()
    assert "timeout" not in snapshot
