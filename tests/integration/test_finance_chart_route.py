"""Integration tests for the finance chart artifact endpoint."""

from __future__ import annotations

import json
import pandas as pd
import pytest


def test_finance_chart_route_returns_summary(client) -> None:
    """The chart endpoint should return derived metadata for available candles."""

    response = client.get(
        "/api/v1/finance/chart",
        params={"symbol": "BTCUSD", "timeframe": "1h", "limit": 20},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["symbol"] == "BTCUSD"
    assert payload["timeframe"] == "1h"
    assert len(payload["rows"]) == 20
    assert len(payload["details"]) == len(payload["rows"])

    selected = payload["selected"]
    assert selected is not None
    assert selected["ts"] == payload["rows"][-1]["ts"]
    assert "changePct" in selected
    # The enriched payload should expose ready-to-render analytics so the UI
    # can display candle details without recalculating them.
    assert selected["range"] == pytest.approx(selected["high"] - selected["low"])
    assert selected["body"] == pytest.approx(selected["close"] - selected["open"])
    assert "bodyPct" in selected
    assert selected["upperWick"] >= 0
    assert selected["lowerWick"] >= 0
    assert selected["direction"] in {"bullish", "bearish", "neutral"}
    last_detail = payload["details"][-1]
    assert last_detail["ts"] == selected["ts"]
    assert last_detail["changeAbs"] == pytest.approx(selected["changeAbs"])
    assert last_detail["direction"] == selected["direction"]
    chart_range = payload["range"]
    assert chart_range["firstTs"] < chart_range["lastTs"]
    assert chart_range["totalVolume"] > 0
    assert payload["overlays"] == []


@pytest.mark.usefixtures("ohlcv_frame")
def test_finance_chart_route_respects_selected_ts(client, ohlcv_frame) -> None:
    """Selecting a candle by timestamp should surface the expected change metrics."""

    target_index = 5
    target_row = ohlcv_frame.iloc[target_index]
    previous_close = ohlcv_frame.iloc[target_index - 1]["c"]
    # Compute the absolute and percentage change expected by the API payload.
    expected_abs = float(target_row["c"] - previous_close)
    expected_pct = 0.0 if previous_close == 0 else (expected_abs / float(previous_close)) * 100

    response = client.get(
        "/api/v1/finance/chart",
        params={
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "limit": 20,
            "selectedTs": int(target_row["ts"]),
        },
    )
    payload = response.json()
    assert response.status_code == 200
    selected = payload["selected"]
    assert selected["ts"] == int(target_row["ts"])
    assert selected["changeAbs"] == pytest.approx(expected_abs)
    assert selected["changePct"] == pytest.approx(expected_pct, rel=1e-6)
    detail = payload["details"][target_index]
    assert detail["range"] == pytest.approx(target_row["h"] - target_row["l"])
    assert detail["direction"] in {"bullish", "bearish", "neutral"}


def test_finance_chart_route_handles_empty_dataset(client, monkeypatch) -> None:
    """Providers returning empty frames should yield an empty artefact response."""

    provider = client.app.state.provider
    empty_frame = pd.DataFrame(columns=["ts", "o", "h", "l", "c", "v"])

    def _empty_get_ohlcv(*args, **kwargs):
        return empty_frame

    monkeypatch.setattr(provider, "get_ohlcv", _empty_get_ohlcv)
    response = client.get(
        "/api/v1/finance/chart",
        params={"symbol": "BTCUSD", "timeframe": "1h", "limit": 20},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "empty"
    assert payload["rows"] == []
    assert payload["selected"] is None
    assert payload["range"] is None
    assert payload["details"] == []
    assert payload["overlays"] == []


def test_finance_chart_route_returns_requested_overlays(client) -> None:
    """Overlay toggles should emit SMA/EMA series ready for the UI chart."""

    response = client.get(
        "/api/v1/finance/chart",
        params={
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "limit": 120,
            "overlays": json.dumps(
                [
                    {"id": "sma-50", "type": "sma", "window": 50},
                    {"id": "ema-21", "type": "ema", "window": 21},
                ]
            ),
        },
    )

    payload = response.json()
    assert response.status_code == 200
    overlays = payload["overlays"]
    assert len(overlays) == 2
    assert len(payload["details"]) == len(payload["rows"])
    sma_overlay = next(series for series in overlays if series["id"] == "sma-50")
    ema_overlay = next(series for series in overlays if series["id"] == "ema-21")
    assert sma_overlay["type"] == "sma"
    assert ema_overlay["type"] == "ema"
    assert len(sma_overlay["points"]) == len(payload["rows"])
    assert len(ema_overlay["points"]) == len(payload["rows"])
    assert sma_overlay["points"][0]["value"] is None
    assert ema_overlay["points"][0]["value"] is not None


def test_finance_chart_route_rejects_duplicate_overlays(client) -> None:
    """Duplicate overlay identifiers should yield a validation error."""

    response = client.get(
        "/api/v1/finance/chart",
        params={
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "limit": 120,
            "overlays": json.dumps(
                [
                    {"id": "sma-50", "type": "sma", "window": 50},
                    {"id": "sma-50", "type": "ema", "window": 21},
                ]
            ),
        },
    )

    assert response.status_code == 400
