"""Runtime checks ensuring MCP server registration stays consistent."""

from __future__ import annotations

import pytest

pytest.importorskip("fastmcp")

from chart_mcp import mcp_main


class _DummyServer:
    """Minimal subset of the FastMCP API needed for registration tests."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def tool(self, name: str):  # type: ignore[override]
        """Return a decorator recording the tool name for later assertions."""

        def _decorator(fn):  # type: ignore[no-untyped-def]
            self.names.append(name)
            return fn

        return _decorator


def test_register_exposes_expected_tools() -> None:
    """The MCP entrypoint should publish all documented tool names."""

    server = _DummyServer()
    mcp_main.register(server)  # type: ignore[arg-type]
    registered = set(server.names)
    expected = set(mcp_main.REGISTERED_TOOL_NAMES)
    assert expected.issubset(registered), registered
