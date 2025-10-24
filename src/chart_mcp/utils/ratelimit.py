"""In-memory rate limiting primitives with Playwright bypass support."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable, Deque, DefaultDict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from chart_mcp.utils.errors import TooManyRequests

Clock = Callable[[], float]


class RateLimiter:
    """Token bucket style limiter that enforces a per-minute quota."""

    def __init__(
        self,
        requests_per_minute: int,
        *,
        bypass: bool = False,
        clock: Clock | None = None,
    ) -> None:
        """Configure the limiter and storage buckets."""

        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self._limit = requests_per_minute
        self._window_seconds = 60.0
        self._bypass = bypass
        self._clock: Clock = clock or time.monotonic
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def acquire(self, key: str) -> None:
        """Record a call for *key* and raise if the quota would be exceeded."""

        if self._bypass:
            return
        now = self._clock()
        window_start = now - self._window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= self._limit:
                raise TooManyRequests("Rate limit exceeded for caller")
            bucket.append(now)


KeyFunc = Callable[[Request], str]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that applies :class:`RateLimiter` to HTTP requests."""

    def __init__(
        self,
        app,
        limiter: RateLimiter,
        *,
        key_func: KeyFunc | None = None,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._key_func: KeyFunc = key_func or self._client_host_key

    @staticmethod
    def _client_host_key(request: Request) -> str:
        """Map a request to a stable key derived from its client address."""

        client = request.client
        return client.host if client else "global"

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        """Gate each request through the configured limiter."""

        key = self._key_func(request)
        try:
            self._limiter.acquire(key)
        except TooManyRequests as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_payload())
        return await call_next(request)


__all__ = ["RateLimiter", "RateLimitMiddleware"]

