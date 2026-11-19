"""In-memory per-key token-bucket rate limiting middleware.

Production note: this state is per-process. Swap `_BUCKETS` for a shared store
(Redis `INCR`/`EXPIRE`) to rate-limit across horizontally-scaled replicas.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.correlation import get_request_id
from app.core.security import API_KEY_HEADER


class _Bucket:
    __slots__ = ("tokens", "updated")

    def __init__(self, tokens: float, updated: float) -> None:
        self.tokens = tokens
        self.updated = updated


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int | None = None) -> None:
        super().__init__(app)
        self.capacity = float(per_minute or settings.rate_limit_per_minute)
        self.refill_per_sec = self.capacity / 60.0
        self._buckets: dict[str, _Bucket] = {}

    def _key(self, request: Request) -> str:
        return request.headers.get(API_KEY_HEADER) or (
            request.client.host if request.client else "anonymous"
        )

    async def dispatch(self, request: Request, call_next):
        # Only throttle the API surface; leave docs/openapi/health untouched.
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
            return await call_next(request)

        key = self._key(request)
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(self.capacity, now)
            self._buckets[key] = bucket
        # Refill
        elapsed = now - bucket.updated
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_per_sec)
        bucket.updated = now

        if bucket.tokens < 1.0:
            retry_after = max(1, int((1.0 - bucket.tokens) / self.refill_per_sec))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded. Please retry later.",
                        "request_id": get_request_id(),
                    }
                },
            )
        bucket.tokens -= 1.0
        return await call_next(request)
