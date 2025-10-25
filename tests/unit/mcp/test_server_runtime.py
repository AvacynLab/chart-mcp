"""Smoke tests ensuring MCP entrypoint registers all expected tools."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types


def _install_fastmcp_stub() -> None:
    """Inject a deterministic ``fastmcp`` replacement tailored for the tests."""

    sys.modules.pop("fastmcp", None)

    stub_module = types.ModuleType("fastmcp")

    class _StubFastMCP:
        """Record tool registrations and stdio sessions for assertions."""

        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self.decorated: list[str] = []
            self.run_calls: list[dict[str, object]] = []

        def tool(  # type: ignore[no-untyped-def]
            self, name_or_fn=None, *, name=None, **_: object
        ):
            """Return a decorator adding the resolved name to ``decorated``."""

            resolved = name_or_fn if isinstance(name_or_fn, str) else name
            if resolved is None:
                raise AssertionError("Tool name must be provided in tests")

            def decorator(fn):  # type: ignore[no-untyped-def]
                self.decorated.append(resolved)
                return fn

            return decorator

        async def run_stdio_async(  # type: ignore[no-untyped-def]
            self, show_banner: bool = True, log_level: str | None = None
        ) -> None:
            """Capture invocation metadata instead of opening real pipes."""

            self.run_calls.append({"show_banner": show_banner, "log_level": log_level})

    # Provide both ``FastMCP`` (used at runtime) and ``MCPServer`` (legacy import)
    # symbols so that all code paths remain satisfied under the stubbed module.
    stub_module.FastMCP = _StubFastMCP  # type: ignore[attr-defined]
    stub_module.MCPServer = _StubFastMCP  # type: ignore[attr-defined]
    sys.modules["fastmcp"] = stub_module


def test_tools_registered() -> None:
    """The register() helper should attach every public tool identifier."""

    _install_fastmcp_stub()
    module = importlib.reload(importlib.import_module("chart_mcp.mcp_main"))

    class DummyServer:
        """In-memory registry collecting the decorated tool names."""

        def __init__(self) -> None:
            self.names: list[str] = []

        def tool(self, name):  # type: ignore[no-untyped-def]
            """Record the tool name and return a passthrough decorator."""

            def decorator(fn):  # type: ignore[no-untyped-def]
                self.names.append(name)
                return fn

            return decorator

    server = DummyServer()
    module.register(server)

    expected = {
        "get_crypto_data",
        "compute_indicator",
        "identify_support_resistance",
        "detect_chart_patterns",
        "generate_analysis_summary",
    }
    assert expected.issubset(set(server.names))


def test_mcp_server_adapter_invokes_fastmcp() -> None:
    """The thin adapter should forward calls to the FastMCP stub."""

    _install_fastmcp_stub()
    module = importlib.reload(importlib.import_module("chart_mcp.mcp_main"))
    server = module.MCPServer(name="demo", instructions="desc")

    # Register a tool and ensure the stub recorded the name through the adapter.
    server.tool("demo_tool")(lambda: None)
    assert server._inner.decorated == ["demo_tool"]  # type: ignore[attr-defined]

    # ``serve_stdio`` should call the FastMCP stub with the banner disabled.
    asyncio.run(server.serve_stdio())
    assert server._inner.run_calls == [  # type: ignore[attr-defined]
        {"show_banner": False, "log_level": None}
    ]
