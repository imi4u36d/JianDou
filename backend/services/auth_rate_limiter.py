from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from backend.config import settings


class SlidingWindowRateLimiter:
    """Small in-process limiter for authentication entrypoints."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> int:
        if limit <= 0 or window_seconds <= 0:
            return 0
        now = self._clock()
        hits = self._hits[key]
        cutoff = now - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(window_seconds - (now - hits[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limit_exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return len(hits)

    def clear(self) -> None:
        self._hits.clear()


auth_rate_limiter = SlidingWindowRateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_auth_rate_limit(request: Request, bucket: str, limit: int) -> None:
    ip = client_ip(request)
    auth_rate_limiter.check(
        f"{bucket}:{ip}",
        limit=limit,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )


def check_auth_subject_rate_limit(request: Request, bucket: str, subject: str, limit: int) -> None:
    ip = client_ip(request)
    normalized_subject = (subject or "").strip().lower() or "unknown"
    auth_rate_limiter.check(
        f"{bucket}:{ip}:{normalized_subject}",
        limit=limit,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
