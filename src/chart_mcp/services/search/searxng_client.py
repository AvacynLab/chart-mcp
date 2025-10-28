"""HTTP client dedicated to querying a self-hosted SearxNG instance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol, Sequence

import httpx

from chart_mcp.utils.errors import UpstreamError


class SearchClientProtocol(Protocol):
    """Protocol describing the subset of client behaviour used by the API."""

    def search(
        self,
        *,
        query: str,
        categories: Sequence[str] | None = None,
        time_range: str | None = None,
        language: str = "fr",
    ) -> List["SearchResult"]:
        """Execute the search and return normalized results."""


@dataclass(slots=True)
class SearchResult:
    """Normalized representation of a single search result item."""

    title: str
    url: str
    snippet: str
    source: str
    score: float


class SearxNGClient:
    """Small synchronous wrapper around the SearxNG JSON API.

    The official SearxNG instance exposes a ``/search`` endpoint returning a JSON
    payload when ``format=json`` is provided. The schema is moderately stable
    across releases and includes information about the originating engine, a
    numeric score and a short snippet. This client normalises the shape into
    :class:`SearchResult` objects so downstream FastAPI routes can focus on
    access control and pagination while leaving error handling and response
    parsing here.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be provided for SearxNGClient")
        # ``rstrip('/')`` keeps the request assembly simple regardless of whether
        # operators configured the environment variable with a trailing slash.
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def search(
        self,
        *,
        query: str,
        categories: Sequence[str] | None = None,
        time_range: str | None = None,
        language: str = "fr",
    ) -> List[SearchResult]:
        """Fetch and normalise search results from SearxNG.

        The query is forwarded to the configured SearxNG instance. Optional categories
        and time range parameters are passed verbatim, while ``language`` defaults to
        French so the upstream engines bias towards francophone sources.
        """
        trimmed_query = query.strip()
        if not trimmed_query:
            raise ValueError("query must not be empty")
        params: dict[str, str] = {
            "q": trimmed_query,
            "format": "json",
            "language": language,
            "safesearch": "0",
        }
        if categories:
            params["categories"] = ",".join(self._normalise_categories(categories))
        if time_range:
            params["time_range"] = time_range
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as http_client:
                response = http_client.get(f"{self._base_url}/search", params=params)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Failed to query SearxNG: {exc}") from exc
        if response.status_code >= 500:
            raise UpstreamError(
                f"SearxNG responded with {response.status_code}",
                details={"status_code": response.status_code},
            )
        if response.status_code >= 400:
            raise UpstreamError(
                "SearxNG request rejected",
                details={"status_code": response.status_code, "body": response.text},
            )
        payload = response.json()
        results = payload.get("results", [])
        normalized: List[SearchResult] = []
        for item in results:
            title = str(item.get("title", ""))
            url = str(item.get("url", ""))
            snippet = str(item.get("content", ""))
            source = str(item.get("engine", "unknown"))
            score_raw = item.get("score", 0.0)
            try:
                score = float(score_raw) if score_raw is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0
            normalized.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=source,
                    score=score,
                )
            )
        return normalized

    @staticmethod
    def _normalise_categories(values: Iterable[str]) -> List[str]:
        """Return cleaned, lower-cased categories without duplicates."""
        cleaned: List[str] = []
        for value in values:
            candidate = value.strip().lower()
            if not candidate or candidate in cleaned:
                continue
            cleaned.append(candidate)
        return cleaned
