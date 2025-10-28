"""Authentication utilities for FastAPI routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chart_mcp.config import settings
from chart_mcp.utils.errors import Forbidden, Unauthorized

_security = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_security)]
RegularUserHeader = Annotated[
    str | None,
    Header(alias="X-Session-User", convert_underscores=False),
]


def require_token(credentials: BearerCredentials) -> None:
    """Ensure the provided Bearer token matches the configured API token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Missing Bearer token")
    if credentials.credentials != settings.api_token:
        raise Unauthorized("Invalid token provided")


def require_regular_user(user_type: RegularUserHeader = None) -> None:
    """Ensure the request originates from a regular (non-guest) session."""
    # The cahier des charges enforces ``X-Session-User: regular`` as the explicit
    # contract between the backend and the front/agent clients. Using the exact
    # header name also keeps the API specification in sync with the MCP tooling
    # documentation that references this guard.
    if user_type is None:
        raise Forbidden("Regular session required", code="forbidden:chat")
    if user_type.lower() != "regular":
        raise Forbidden("Regular session required", code="forbidden:chat")


__all__ = ["require_token", "require_regular_user"]
