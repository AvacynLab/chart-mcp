"""Common type aliases shared across the application.

These aliases intentionally model JSON-compatible payloads to give the type
checker more context than plain ``Any`` values. They are reused by the error
handling, streaming and SSE helpers to ensure responses stay serialisable.
"""

from __future__ import annotations

from typing import Dict, List, TypeAlias, Union

# NOTE:
# ``JSONValue`` is intentionally conservative: lists and dictionaries use
# ``object`` instead of recursive aliases so that pydantic can construct schemas
# without hitting recursion depth limits while still avoiding ``Any``.
JSONPrimitive: TypeAlias = Union[str, int, float, bool, None]
JSONValue: TypeAlias = Union[JSONPrimitive, Dict[str, object], List[object]]
JSONDict: TypeAlias = Dict[str, JSONValue]

__all__ = ["JSONPrimitive", "JSONValue", "JSONDict"]
