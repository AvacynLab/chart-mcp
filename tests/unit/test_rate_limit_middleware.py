"""Tests covering the HTTP middleware integration for rate limiting."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from chart_mcp.utils.errors import ApiError, TooManyRequests, api_error_handler
from chart_mcp.utils.ratelimit import RateLimiter, RateLimitMiddleware


def build_app(limiter: RateLimiter) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=limiter, key_func=lambda _: "global")
    app.add_exception_handler(ApiError, api_error_handler)

    @app.get("/")
    def root() -> PlainTextResponse:
        return PlainTextResponse("ok")

    return app


def test_middleware_blocks_excessive_requests() -> None:
    limiter = RateLimiter(1, bypass=False)
    app = build_app(limiter)
    client = TestClient(app)
    assert client.get("/").status_code == 200
    response = client.get("/")
    assert response.status_code == TooManyRequests.status_code
    payload = response.json()
    assert payload["error"]["code"] == TooManyRequests.code


def test_middleware_respects_bypass_flag() -> None:
    limiter = RateLimiter(1, bypass=True)
    app = build_app(limiter)
    client = TestClient(app)
    for _ in range(3):
        assert client.get("/").status_code == 200

