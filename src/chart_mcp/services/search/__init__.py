"""Search service helpers wrapping the SearxNG API."""

from .searxng_client import SearchClientProtocol, SearchResult, SearxNGClient

__all__ = ["SearchClientProtocol", "SearchResult", "SearxNGClient"]
