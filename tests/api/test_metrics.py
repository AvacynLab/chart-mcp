"""Integration tests for the Prometheus metrics endpoint."""

from __future__ import annotations

from chart_mcp.services.metrics import metrics
from prometheus_client import CONTENT_TYPE_LATEST  # type: ignore[import-not-found]


def test_metrics_endpoint_exposes_counters(client) -> None:
    """The /metrics endpoint should return Prometheus-formatted payloads."""
    metrics.reset()
    metrics.record_provider_error("ccxt", "binance", "rate_limit")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST
    body = response.text
    assert "provider_errors_total" in body
    assert "ccxt" in body and "rate_limit" in body
