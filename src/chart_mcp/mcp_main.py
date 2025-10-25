"""Executable MCP server exposing the chart_mcp tools."""

from __future__ import annotations

import asyncio
from typing import Callable, Dict

from loguru import logger

from chart_mcp import mcp_server

try:
    # ``fastmcp`` ships the runtime we rely on to expose MCP tools over stdio.
    from fastmcp import FastMCP
except (
    ImportError
) as exc:  # pragma: no cover - ensures a helpful failure when optional dep is missing
    raise RuntimeError("fastmcp must be installed to launch the chart-mcp MCP server") from exc


class MCPServer:
    """Thin adapter around :class:`fastmcp.FastMCP` with a minimal API surface.

    The upstream library exposes a feature-rich ``FastMCP`` class while the rest of
    the codebase (and the unit tests) expect a much smaller interface: the ability
    to register tools via a decorator and to serve them over stdio.  Wrapping the
    upstream class keeps the implementation explicit, prevents the production code
    from depending on private attributes, and ensures the tests can replace
    ``FastMCP`` with in-memory fakes.
    """

    def __init__(self, name: str | None = None, instructions: str | None = None) -> None:
        """Store the configured FastMCP instance and basic metadata."""
        self._inner = FastMCP(name=name, instructions=instructions)

    def tool(
        self,
        name_or_fn: str | Callable[..., object] | None = None,
        *,
        name: str | None = None,
        **kwargs: object,
    ) -> Callable[[Callable[..., object]], object]:
        """Proxy tool registration to the underlying FastMCP instance.

        The wrapper keeps the same decorator-based interface while making it easy
        for unit tests to assert the registered tool names via monkeypatched
        ``FastMCP`` implementations.
        """
        return self._inner.tool(name_or_fn, name=name, **kwargs)

    async def serve_stdio(self) -> None:
        """Expose the tools over stdio without displaying the FastMCP banner."""
        await self._inner.run_stdio_async(show_banner=False)

    def __getattr__(self, name: str) -> object:
        """Delegate attribute access to ``FastMCP`` for advanced uses."""
        return getattr(self._inner, name)


# Map the public tool identifiers to their implementation functions. Using an explicit
# dictionary ensures the registration order stays deterministic which simplifies
# debugging and fulfils the expectations of the runtime smoke tests.
_TOOL_BINDINGS: Dict[str, Callable[..., object]] = {
    "get_crypto_data": mcp_server.get_crypto_data,
    "compute_indicator": mcp_server.compute_indicator,
    "identify_support_resistance": mcp_server.identify_support_resistance,
    "detect_chart_patterns": mcp_server.detect_chart_patterns,
    "generate_analysis_summary": mcp_server.generate_analysis_summary,
}

# ``REGISTERED_TOOL_NAMES`` is exported for CI and external consumers that only need
# to introspect which tools the MCP server exposes without importing the bindings
# dictionary itself.  Using a tuple keeps the order deterministic while preventing
# accidental mutation.
REGISTERED_TOOL_NAMES = tuple(_TOOL_BINDINGS.keys())


def register(server: MCPServer) -> None:
    """Attach every chart tool to *server* using stable identifiers."""
    for name, func in _TOOL_BINDINGS.items():
        # The decorator returned by ``server.tool`` wires the callable for remote
        # execution. We immediately apply it so the server is ready once ``main``
        # finishes instantiating the event loop.
        server.tool(name)(func)
    logger.debug("mcp.tools_registered", tools=list(_TOOL_BINDINGS))


async def main() -> None:
    """Create an MCP server and serve the tools over stdio."""
    server = MCPServer(
        name="chart-mcp",
        instructions="Analyse crypto pédagogique. Aucun conseil d'investissement.",
    )
    register(server)
    try:
        await server.serve_stdio()
    except Exception:  # pragma: no cover - unexpected crashes must bubble with context
        logger.exception("mcp.server_crash")
        raise


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["register", "main", "REGISTERED_TOOL_NAMES", "MCPServer"]
