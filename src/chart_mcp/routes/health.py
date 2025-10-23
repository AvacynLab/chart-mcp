"""Health endpoint reporting service status."""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter

from chart_mcp import __version__
from chart_mcp.config import settings

_router_start = time.time()

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Return uptime, version and configured exchange."""

    uptime = time.time() - _router_start
    return {
        "status": "ok",
        "version": __version__,
        "uptime": uptime,
        "exchange": settings.exchange,
        "checked_at": datetime.utcnow().isoformat(),
    }
