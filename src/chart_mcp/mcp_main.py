"""MCP stdio entrypoint exposing chart analysis tooling."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from fastmcp import FastMCP

from chart_mcp import mcp_server as tools

REGISTERED_TOOL_NAMES = (
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
)
"""Ordered tuple listing every tool exposed over the MCP transport."""


def _df_records(payload: pd.DataFrame | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert Pandas frames or pre-serialised rows into JSON-friendly records.

    The REST surface manipulates Pandas objects for convenience and numerical
    precision. This helper keeps that internal contract intact while ensuring
    that the MCP server only emits plain dictionaries, which are naturally
    serialisable over stdio transports. For backwards-compatibility we also
    accept already-serialised sequences of mappings.
    """
    if isinstance(payload, pd.DataFrame):
        records = payload.reset_index(drop=True).to_dict(orient="records")
        return [{str(key): value for key, value in row.items()} for row in records]
    return [{str(key): value for key, value in dict(item).items()} for item in payload]


class MCPServer(FastMCP):
    """Compatibility subclass exposing the ``serve_stdio`` helper."""

    async def serve_stdio(self) -> None:
        """Run the stdio loop without printing the SDK banner."""
        await self.run_stdio_async(show_banner=False)


def register(server: MCPServer) -> None:
    """Attach every public MCP tool to *server* with JSON conversion."""
    server.tool("get_crypto_data")(
        lambda symbol, timeframe, limit=500, start=None, end=None: _df_records(
            tools.get_crypto_data(symbol, timeframe, limit=limit, start=start, end=end)
        )
    )
    server.tool("compute_indicator")(
        lambda symbol, timeframe, indicator, params=None: _df_records(
            tools.compute_indicator(symbol, timeframe, indicator, params or {})
        )
    )
    server.tool("identify_support_resistance")(tools.identify_support_resistance)
    server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
    server.tool("generate_analysis_summary")(
        lambda payload: tools.generate_analysis_summary(payload)
    )


async def main() -> None:
    """Launch the MCP server over stdio using the default tool registry."""
    server = MCPServer()
    register(server)
    await server.serve_stdio()


if __name__ == "__main__":
    asyncio.run(main())
