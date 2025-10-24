"""Integration tests covering quote, fundamentals, news and screener endpoints."""

from __future__ import annotations


def test_quote_endpoint_returns_snapshot(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/quote", params={"symbol": "nvda"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["currency"] == "USD"
    assert payload["changePct"] == 2.0


def test_quote_invalid_symbol_length(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/quote", params={"symbol": "x"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_fundamentals_returns_metrics(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/fundamentals", params={"symbol": "btcusd"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSD"
    assert payload["marketCap"] == 1.2e12
    assert payload["week52High"] == 72000.0


def test_news_pagination(client) -> None:  # noqa: ANN001
    response = client.get(
        "/api/v1/finance/news",
        params={"symbol": "nvda", "limit": 1, "offset": 0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert len(payload["items"]) == 1
    first_item = payload["items"][0]
    assert first_item["id"] == "nvda-1"


def test_news_invalid_limit(client) -> None:  # noqa: ANN001
    response = client.get(
        "/api/v1/finance/news",
        params={"symbol": "nvda", "limit": 100},
    )
    # Pydantic now rejects values above the declarative upper bound.
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_screen_filters_by_sector_and_score(client) -> None:  # noqa: ANN001
    response = client.get(
        "/api/v1/finance/screen",
        params={"sector": "technology", "minScore": 0.85},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    assert payload["results"][0]["symbol"] == "NVDA"


def test_screen_rejects_invalid_min_score(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/screen", params={"minScore": 2})
    # Validation happens at the request schema layer to guarantee consistent error payloads.
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_screen_rejects_limit_above_cap(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/screen", params={"limit": 500})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_quote_returns_not_found_for_missing_symbol(client) -> None:  # noqa: ANN001
    response = client.get("/api/v1/finance/quote", params={"symbol": "msft"})
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"

