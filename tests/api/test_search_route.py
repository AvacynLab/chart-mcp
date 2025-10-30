"""Integration tests for the SearxNG search route."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chart_mcp.services.search import SearchResult
from chart_mcp.utils.errors import UpstreamError


class StubSearchClient:
    """Deterministic SearxNG client used to exercise the HTTP route."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], str | None]] = []

    def search(
        self,
        *,
        query: str,
        categories: list[str] | None,
        time_range: str | None,
    ) -> list[SearchResult]:
        """Record the call parameters and return a deterministic payload."""
        self.calls.append((query, categories or [], time_range))
        return [
            SearchResult(
                title="Bitcoin rebounds",
                url="https://example.com/bitcoin",
                snippet="BTC regains the 70k handle amid renewed interest.",
                source="gnews",
                score=9.1,
            )
        ]


class FailingSearchClient(StubSearchClient):
    """Stub raising ``UpstreamError`` to test error propagation."""

    def search(self, *, query: str, categories: list[str] | None, time_range: str | None):
        """Simulate an upstream failure by raising ``UpstreamError`` consistently."""
        raise UpstreamError("boom", details={"query": query})


def test_search_route_returns_payload(client, test_app) -> None:
    stub = StubSearchClient()
    client.app.state.search_client = stub

    response = client.get(
        "/api/v1/search",
        params={"q": "bitcoin breakout", "categories": "News,Science", "time_range": "day"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "bitcoin breakout"
    assert payload["categories"] == ["news", "science"]
    assert payload["results"][0]["title"] == "Bitcoin rebounds"
    assert stub.calls == [("bitcoin breakout", ["news", "science"], "day")]


def test_search_route_returns_enriched_results(client) -> None:
    """The HTTP layer should normalise categories and expose result metadata."""
    stub = StubSearchClient()
    client.app.state.search_client = stub

    response = client.get(
        "/api/v1/search",
        params={
            "q": "ethereum merge",
            "categories": "News,Tech,DeFi",
            "time_range": "week",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "ethereum merge"
    assert payload["categories"] == ["news", "tech", "defi"]
    assert payload["time_range"] == "week"
    result = payload["results"][0]
    assert set(result.keys()) == {"title", "url", "snippet", "source", "score"}
    assert result["score"] == pytest.approx(9.1)


def test_search_route_requires_configuration(client) -> None:
    client.app.state.search_client = None

    response = client.get("/api/v1/search", params={"q": "eth"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_search_route_propagates_upstream_error(client) -> None:
    client.app.state.search_client = FailingSearchClient()

    response = client.get("/api/v1/search", params={"q": "btc"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"


def test_search_route_requires_authentication(test_app) -> None:
    test_app.state.search_client = StubSearchClient()
    with TestClient(test_app) as anonymous:
        response = anonymous.get("/api/v1/search", params={"q": "btc"})
    assert response.status_code == 401
