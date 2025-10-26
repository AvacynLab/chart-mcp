from __future__ import annotations

import asyncio
from typing import Callable

from fastmcp import FastMCP

from chart_mcp import mcp_server as tools

REGISTERED_TOOL_NAMES = (
    "get_crypto_data",
    "compute_indicator",
    "identify_support_resistance",
    "detect_chart_patterns",
    "generate_analysis_summary",
)


class MCPServer:
    """Adapter exposing a minimal API over :class:`fastmcp.FastMCP`."""

    def __init__(self, name: str | None = None, instructions: str | None = None) -> None:
        self._inner = FastMCP(name=name, instructions=instructions)

    def tool(
        self,
        name_or_fn: str | None = None,
        *,
        name: str | None = None,
        **kwargs: object,
    ) -> Callable[[Callable[..., object]], object]:
        """Delegate tool registration to the underlying FastMCP instance."""
        return self._inner.tool(name_or_fn, name=name, **kwargs)

    async def serve_stdio(self) -> None:
        """Expose the registered tools over stdio without banners."""
        await self._inner.run_stdio_async(show_banner=False)

    def __getattr__(self, item: str) -> object:
        return getattr(self._inner, item)


def register(server: MCPServer) -> None:
    """Attach every exported MCP tool to *server*.

    The function is intentionally compact so the CI smoke test can import this
    module and verify that all expected tool names are registered.
    """
    server.tool("get_crypto_data")(tools.get_crypto_data)
    server.tool("compute_indicator")(tools.compute_indicator)
    server.tool("identify_support_resistance")(tools.identify_support_resistance)
    server.tool("detect_chart_patterns")(tools.detect_chart_patterns)
    server.tool("generate_analysis_summary")(tools.generate_analysis_summary)


async def main() -> None:
    """Instantiate an :class:`MCPServer` and serve it over stdio."""
    server = MCPServer()
    register(server)
    await server.serve_stdio()


if __name__ == "__main__":
    asyncio.run(main())
