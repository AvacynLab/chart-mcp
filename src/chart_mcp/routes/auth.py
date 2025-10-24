"""Authentication utilities for FastAPI routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chart_mcp.config import settings
from chart_mcp.utils.errors import Unauthorized

_security = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_security)]


def require_token(credentials: BearerCredentials) -> None:
    """Ensure the provided Bearer token matches the configured API token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Missing Bearer token")
    if credentials.credentials != settings.api_token:
        raise Unauthorized("Invalid token provided")


__all__ = ["require_token"]
