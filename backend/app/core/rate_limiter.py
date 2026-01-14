"""Rate limiting middleware and utilities using in-memory storage.

Copyright 2025 milbert.ai
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Callable, Dict

from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryRateLimitStorage:
    """Thread-safe in-memory storage for rate limiting."""

    def __init__(self):
        self._data: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._lock = Lock()

    def incr(self, key: str, window_start: int) -> int:
        """Increment counter for key and window."""
        full_key = f"{key}:{window_start}"
        with self._lock:
            if full_key not in self._data:
                self._data[full_key] = {"count": 0, "expires": window_start + 86400}
            self._data[full_key]["count"] += 1
            return self._data[full_key]["count"]

    def cleanup(self):
        """Remove expired entries."""
        current_time = int(time.time())
        with self._lock:
            expired_keys = [
                k for k, v in self._data.items()
                if v.get("expires", 0) < current_time
            ]
            for k in expired_keys:
                del self._data[k]


# Global storage instance
_storage = InMemoryRateLimitStorage()


class RateLimiter:
    """
    Token bucket rate limiter using in-memory storage.

    Supports multiple time windows for flexible rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int | None = None,
        requests_per_hour: int | None = None,
        requests_per_day: int | None = None,
        key_prefix: str = "rate_limit",
    ):
        self.requests_per_minute = requests_per_minute or settings.rate_limit_per_minute
        self.requests_per_hour = requests_per_hour or settings.rate_limit_per_hour
        self.requests_per_day = requests_per_day or 10000
        self.key_prefix = key_prefix

    def _get_key(self, identifier: str, window: str) -> str:
        """Generate key for rate limiting."""
        return f"{self.key_prefix}:{window}:{identifier}"

    def _check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check and update rate limit for a given window.

        Returns:
            Tuple of (allowed, current_count, reset_time)
        """
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)

        current_count = _storage.incr(key, window_start)
        reset_time = window_start + window_seconds

        return current_count <= limit, current_count, reset_time

    def check_limit(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier (user ID, IP address, etc.)

        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        limits = [
            ("minute", self.requests_per_minute, 60),
            ("hour", self.requests_per_hour, 3600),
            ("day", self.requests_per_day, 86400),
        ]

        info = {}
        for window, limit, seconds in limits:
            key = self._get_key(identifier, window)
            allowed, current, reset = self._check_rate_limit(key, limit, seconds)
            info[window] = {
                "limit": limit,
                "remaining": max(0, limit - current),
                "reset": reset,
            }
            if not allowed:
                return False, info

        return True, info

    def reset(self, identifier: str) -> None:
        """Reset rate limits for an identifier (no-op for in-memory)."""
        pass


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        requests_per_minute: int | None = None,
        requests_per_hour: int | None = None,
        key_func: Callable[[Request], str] | None = None,
    ):
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )
        self.key_func = key_func or self._default_key_func

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Get identifier from request (IP by default)."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        identifier = self.key_func(request)

        try:
            allowed, info = self.limiter.check_limit(identifier)
        except Exception as e:
            logger.warning(f"Rate limiting unavailable: {e}")
            return await call_next(request)

        if not allowed:
            for window, data in info.items():
                if data["remaining"] == 0:
                    retry_after = data["reset"] - int(time.time())
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                        headers={
                            "X-RateLimit-Limit": str(data["limit"]),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(data["reset"]),
                            "Retry-After": str(retry_after),
                        },
                    )

        response = await call_next(request)

        minute_info = info.get("minute", {})
        if minute_info:
            response.headers["X-RateLimit-Limit"] = str(minute_info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(minute_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(minute_info.get("reset", 0))

        return response


def rate_limit(
    requests_per_minute: int | None = None,
    requests_per_hour: int | None = None,
    key_prefix: str = "api",
):
    """
    Dependency for rate limiting specific endpoints.

    Usage:
        @router.get("/endpoint", dependencies=[Depends(rate_limit(10, 100))])
        async def endpoint():
            ...
    """
    limiter = RateLimiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        key_prefix=key_prefix,
    )

    async def check(request: Request):
        user = getattr(request.state, "user", None)
        if user:
            identifier = str(user.id)
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                identifier = forwarded.split(",")[0].strip()
            else:
                identifier = request.client.host if request.client else "unknown"

        try:
            allowed, info = limiter.check_limit(identifier)
        except Exception as e:
            logger.warning(f"Rate limiting check failed: {e}")
            return

        if not allowed:
            for window, data in info.items():
                if data["remaining"] == 0:
                    retry_after = data["reset"] - int(time.time())
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded for {window}. Retry after {retry_after}s.",
                        headers={"Retry-After": str(retry_after)},
                    )

    return check


# Pre-configured limiters for common use cases
strict_rate_limit = rate_limit(requests_per_minute=10, requests_per_hour=100)
auth_rate_limit = rate_limit(requests_per_minute=5, requests_per_hour=30, key_prefix="auth")
api_rate_limit = rate_limit(requests_per_minute=60, requests_per_hour=1000, key_prefix="api")
