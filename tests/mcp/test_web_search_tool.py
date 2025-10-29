from __future__ import annotations

from typing import Iterable, List

import pytest

from chart_mcp import mcp_server
from chart_mcp.services.search.searxng_client import SearchResult
from chart_mcp.utils.errors import UpstreamError


class SpySearchClient:
    """Spy client capturing search invocations for assertions."""

    def __init__(self) -> None:
        self.calls: List[dict[str, object]] = []
        self._results = [
            SearchResult(
                title="Bitcoin outlook",
                url="https://example.com/btc-outlook",
                snippet="Market recap",
                source="crypto-news",
                score=0.92,
            ),
            SearchResult(
                title="On-chain metrics",
                url="https://example.com/on-chain",
                snippet="Data dive",
                source="analytics",
                score=0.73,
            ),
        ]

    def search(
        self,
        *,
        query: str,
        categories: Iterable[str] | None = None,
        time_range: str | None = None,
        language: str = "fr",
    ) -> List[SearchResult]:
        """Return canned results while recording the invocation."""
        self.calls.append(
            {
                "query": query,
                "categories": list(categories or []),
                "time_range": time_range,
                "language": language,
            }
        )
        return self._results


class FailingSearchClient(SpySearchClient):
    """Spy variant raising ``UpstreamError`` to simulate SearxNG outages."""

    def search(
        self,
        *,
        query: str,
        categories: Iterable[str] | None = None,
        time_range: str | None = None,
        language: str = "fr",
    ) -> List[SearchResult]:
        """Raise :class:`UpstreamError` instead of returning canned results."""
        super().search(
            query=query,
            categories=categories,
            time_range=time_range,
            language=language,
        )
        raise UpstreamError("searxng unavailable", details={"query": query})


@pytest.fixture
def spy_search_client(monkeypatch: pytest.MonkeyPatch) -> SpySearchClient:
    """Inject the spy client into the MCP server module."""
    original = getattr(mcp_server, "_search_client", None)
    client = SpySearchClient()
    monkeypatch.setattr(mcp_server, "_search_client", client)
    yield client
    monkeypatch.setattr(mcp_server, "_search_client", original)


def test_web_search_normalises_payload(spy_search_client: SpySearchClient) -> None:
    """The MCP tool should normalise categories and serialise results."""
    response = mcp_server.web_search(
        "  Bitcoin Outlook 2024  ",
        categories=[" News", "science", "NEWS"],
        time_range="week",
        language="en",
    )

    assert response["query"] == "Bitcoin Outlook 2024"
    assert response["categories"] == ["news", "science"]
    assert response["time_range"] == "week"
    assert response["language"] == "en"
    assert response["results"] == [
        {
            "title": "Bitcoin outlook",
            "url": "https://example.com/btc-outlook",
            "snippet": "Market recap",
            "source": "crypto-news",
            "score": 0.92,
        },
        {
            "title": "On-chain metrics",
            "url": "https://example.com/on-chain",
            "snippet": "Data dive",
            "source": "analytics",
            "score": 0.73,
        },
    ]

    assert spy_search_client.calls == [
        {
            "query": "Bitcoin Outlook 2024",
            "categories": ["news", "science"],
            "time_range": "week",
            "language": "en",
        }
    ]


def test_web_search_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """A helpful error is raised when SearxNG is disabled."""
    monkeypatch.setattr(mcp_server, "_search_client", None)

    class DummySettings:
        searxng_enabled = False
        searxng_base_url = None
        searxng_timeout = 5.0

    monkeypatch.setattr(mcp_server, "settings", DummySettings())

    with pytest.raises(RuntimeError, match="SearxNG integration is disabled"):
        mcp_server.web_search("btc")


def test_web_search_rejects_blank_query(spy_search_client: SpySearchClient) -> None:
    """Validator should guard against empty or whitespace-only queries."""
    with pytest.raises(ValueError):
        mcp_server.web_search("   ")
    assert spy_search_client.calls == []


def test_web_search_wraps_upstream_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Upstream failures should surface as ``RuntimeError`` with context."""
    failing_client = FailingSearchClient()
    monkeypatch.setattr(mcp_server, "_search_client", failing_client)

    with pytest.raises(RuntimeError, match="SearxNG request failed"):
        mcp_server.web_search("btc breakout")

    assert failing_client.calls == [
        {
            "query": "btc breakout",
            "categories": [],
            "time_range": None,
            "language": "fr",
        }
    ]
