from __future__ import annotations

from typing import Any, Callable, Protocol


class _FunctionTool(Protocol):
    """Minimal protocol capturing the callable behaviour of FastMCP tools."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class FastMCP:
    """Type stub used during static analysis when ``fastmcp`` runtime package is absent."""

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

    async def run_stdio_async(self, *, show_banner: bool = ...) -> None:
        ...
