from __future__ import annotations

from typing import Any, Callable, Protocol

class _FunctionTool(Protocol):
    """Minimal protocol capturing the callable behaviour of MCP tools."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class MCPServer:
    """Type stub mirroring the interface used by :mod:`chart_mcp.mcp_main`."""

    def __init__(self, name: str | None = None, instructions: str | None = None) -> None:
        ...

    def tool(
        self,
        name_or_fn: Callable[..., Any] | str | None = None,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Any]:
        ...

    async def serve_stdio(self) -> None:
        ...


# Backwards compatibility: some callers still import ``FastMCP`` during tests.
class FastMCP(MCPServer):
    """Alias maintained so legacy imports keep functioning."""

    async def run_stdio_async(self, *, show_banner: bool = ...) -> None:
        ...
