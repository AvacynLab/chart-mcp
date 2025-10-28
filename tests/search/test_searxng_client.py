"""Unit tests covering the SearxNG HTTP client."""

from __future__ import annotations

import httpx
import pytest

from chart_mcp.services.search import SearxNGClient
from chart_mcp.utils.errors import UpstreamError


def test_search_returns_normalized_results() -> None:
    """The client should convert the upstream payload into ``SearchResult`` entries."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/search"
        assert request.url.params["q"] == "bitcoin"
        assert request.url.params["categories"] == "news,science"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Bitcoin hits new high",
                        "url": "https://example.com/bitcoin-high",
                        "content": "Bitcoin surged past previous resistance levels.",
                        "engine": "gnews",
                        "score": 12.5,
                    },
                    {
                        "title": "On-chain metrics explained",
                        "url": "https://example.org/onchain",
                        "content": "Deep dive into whale activity.",
                        "engine": "reddit",
                        "score": None,
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = SearxNGClient("http://searx.local", transport=transport)

    results = client.search(query=" bitcoin ", categories=["News", "science"], time_range="day")

    assert len(results) == 2
    assert results[0].title == "Bitcoin hits new high"
    assert results[0].source == "gnews"
    assert results[0].score == pytest.approx(12.5)
    assert results[1].score == pytest.approx(0.0)


def test_search_raises_upstream_error_on_server_failure() -> None:
    """Non-2xx statuses should surface as ``UpstreamError`` for the route handler."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="maintenance")

    client = SearxNGClient("http://searx.local", transport=httpx.MockTransport(handler))

    with pytest.raises(UpstreamError):
        client.search(query="btc", categories=None)


def test_search_wraps_network_errors() -> None:
    """Transport-level exceptions must be converted to ``UpstreamError`` instances."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = SearxNGClient("http://searx.local", transport=httpx.MockTransport(handler))

    with pytest.raises(UpstreamError):
        client.search(query="eth", categories=["news"])
