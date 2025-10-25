"""Entrypoint exposing chart_mcp tools through a FastMCP server."""

from __future__ import annotations

import asyncio
from typing import Iterable

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - import guard for optional dependency
    raise RuntimeError(
        "fastmcp must be installed to start the MCP server."
    ) from exc

from loguru import logger

from chart_mcp import mcp_server


SERVER_NAME = "chart-mcp"
SERVER_INSTRUCTIONS = (
    "Analyse crypto pédagogique uniquement. Aucun conseil d'investissement."
)
REGISTERED_TOOL_NAMES: Iterable[str] = (
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
)


def register(server: FastMCP) -> None:
    """Register all chart MCP tools onto *server* with stable identifiers."""

    mcp_server.register_tools(server)
    logger.debug(
        "mcp.register_tools tools={tools}",
        tools=list(REGISTERED_TOOL_NAMES),
    )


def build_server() -> FastMCP:
    """Instantiate a FastMCP server primed with chart specific settings."""

    server = FastMCP(name=SERVER_NAME, instructions=SERVER_INSTRUCTIONS)
    register(server)
    return server


async def main() -> None:
    """Run the chart MCP server over stdio, logging unexpected failures."""

    server = build_server()
    try:
        await server.run_stdio_async(show_banner=False)
    except Exception:  # pragma: no cover - guard to ensure crash visibility
        logger.exception("mcp.server_crash")
        raise


if __name__ == "__main__":
    asyncio.run(main())
