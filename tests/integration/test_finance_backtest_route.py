"""Integration tests covering the finance backtest endpoint."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from chart_mcp.services.backtest import BacktestService


@pytest.fixture()
def patched_provider(test_app, ohlcv_frame: pd.DataFrame):
    """Ensure the test app provider returns a deterministic frame for BTCUSD."""

    provider = test_app.state.provider
    provider.frame = ohlcv_frame  # type: ignore[attr-defined]
    return provider


def _request_body(**overrides: Any) -> dict[str, Any]:
    """Base payload used across tests with convenient overrides."""

    body: dict[str, Any] = {
        "symbol": "BTCUSD",
        "timeframe": "1h",
        "start": None,
        "end": None,
        "limit": 500,
        "feesBps": 15,
        "slippageBps": 5,
        "strategy": {
            "name": "sma_cross",
            "params": {"fastWindow": 8, "slowWindow": 26},
        },
    }
    body.update(overrides)
    return body


def test_backtest_returns_metrics_and_trades(client, patched_provider) -> None:  # noqa: ANN001
    """Successful executions should return metrics, equity curve and trades."""

    response = client.post("/api/v1/finance/backtest", json=_request_body())
    assert response.status_code == 200
    payload = response.json()

    assert payload["symbol"] == "BTCUSD"
    assert payload["timeframe"] == "1h"
    metrics = payload["metrics"]
    assert set(metrics.keys()) == {
        "totalReturn",
        "cagr",
        "maxDrawdown",
        "winRate",
        "sharpe",
        "profitFactor",
    }
    assert isinstance(payload["equityCurve"], list)
    assert isinstance(payload["trades"], list)


def test_backtest_validates_strategy_schema(client) -> None:  # noqa: ANN001
    """Invalid strategy names should be rejected at validation time."""

    body = _request_body(strategy={"name": "unknown", "params": {}})
    response = client.post("/api/v1/finance/backtest", json=body)
    assert response.status_code == 422


def test_backtest_returns_bad_request_when_provider_empty(client, test_app, monkeypatch) -> None:  # noqa: ANN001
    """If the provider yields an empty frame the API should surface a bad request."""

    def _empty_get_ohlcv(*args, **kwargs):  # type: ignore[no-untyped-def]
        return pd.DataFrame(columns=["ts", "o", "h", "l", "c", "v"])

    provider = test_app.state.provider
    monkeypatch.setattr(provider, "get_ohlcv", _empty_get_ohlcv)

    response = client.post("/api/v1/finance/backtest", json=_request_body())
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert "No market data" in payload["error"]["message"]


def test_backtest_service_reused_from_app_state(test_app) -> None:
    """Ensure the FastAPI application exposes a singleton backtest service."""

    service = test_app.state.backtest_service
    assert isinstance(service, BacktestService)
