"""Regression tests ensuring OpenAPI metadata stays documented."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_includes_descriptive_tags(client: TestClient) -> None:
    """Ensure tag descriptions exist for the documented public surfaces."""
    schema = client.app.openapi()
    tag_index = {entry["name"]: entry["description"] for entry in schema.get("tags", [])}
    expected = {
        "market": "Raw market data retrieval such as normalized OHLCV candles.",
        "indicators": "Technical indicator computations based on OHLCV history.",
        "levels": "Support and resistance level detection with strength scoring.",
        "patterns": "Chart pattern detection including head-and-shoulders heuristics.",
        "analysis": "Aggregated analysis summaries mixing indicators, levels and patterns.",
        "search": "SearxNG-backed discovery of crypto news, documentation and research.",
        "stream": "Server-Sent Events surfaces streaming the multi-step analysis pipeline.",
    }
    for tag, description in expected.items():
        assert tag in tag_index, f"Missing OpenAPI tag for '{tag}'"
        assert tag_index[tag] == description


def test_openapi_summaries_cover_key_routes(client: TestClient) -> None:
    """Validate that primary endpoints expose non-empty summaries for documentation."""
    schema = client.app.openapi()
    paths = schema.get("paths", {})
    expectations = {
        "/api/v1/market/ohlcv": "Retrieve normalized OHLCV candles",
        "/api/v1/indicators/compute": "Compute a technical indicator",
        "/api/v1/levels": "Identify support and resistance levels",
        "/api/v1/patterns": "Detect chart patterns",
        "/api/v1/analysis/summary": "Generate a comprehensive market analysis",
        "/api/v1/search": "Search crypto intelligence with SearxNG",
        "/stream/analysis": "Stream the multi-step analysis as SSE",
    }
    for route, summary in expectations.items():
        operations = paths.get(route, {})
        assert operations, f"Missing OpenAPI path for {route}"
        operation = operations.get("get") or operations.get("post")
        assert operation is not None, f"Missing HTTP verb for {route}"
        assert operation.get("summary") == summary, (
            f"Unexpected summary for {route}: {operation.get('summary')}"
        )
