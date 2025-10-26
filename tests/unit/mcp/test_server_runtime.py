"""Unit checks for the MCP stdio entrypoint."""

from __future__ import annotations

import importlib

import pandas as pd


def test_tools_registered() -> None:
    """The server should register every declared tool name."""
    module = importlib.import_module("chart_mcp.mcp_main")
    registered: list[str] = []

    class DummyServer:
        """Collect tool names passed through ``tool()`` decorators."""

        def tool(self, name: str):
            def decorator(func):  # type: ignore[no-untyped-def]
                registered.append(name)
                return func

            return decorator

    server = DummyServer()
    module.register(server)

    for expected in module.REGISTERED_TOOL_NAMES:
        assert expected in registered


def test_df_records_normalises_dataframe_indices() -> None:
    """The helper must serialise DataFrame rows into plain dictionaries."""
    module = importlib.import_module("chart_mcp.mcp_main")
    frame = pd.DataFrame(
        [
            {"ts": 1, "value": 10.5},
            {"ts": 2, "value": 11.0},
        ],
        index=[5, 6],
    )

    result = module._df_records(frame)

    assert result == [
        {"ts": 1, "value": 10.5},
        {"ts": 2, "value": 11.0},
    ]


def test_df_records_accepts_pre_serialised_rows() -> None:
    """Already serialised payloads should be returned unchanged."""
    module = importlib.import_module("chart_mcp.mcp_main")
    payload = [{"ts": 1, "o": 10.0}]

    assert module._df_records(payload) == payload
