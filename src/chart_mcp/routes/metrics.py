"""Prometheus metrics exposition endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response

from chart_mcp.services.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    include_in_schema=False,
)
async def metrics_endpoint() -> Response:
    """Expose application metrics using the Prometheus text format."""
    payload = metrics.render()
    return Response(content=payload, media_type=metrics.content_type)


__all__ = ["router", "metrics_endpoint"]
