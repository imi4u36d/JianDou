from __future__ import annotations

import time
import uuid
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


class RedisSlidingWindowRateLimiter:
    """Redis-backed sliding-window limiter for multi-worker deployments."""

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def check(self, key: str, *, limit: int, window_seconds: int) -> int:
        if limit <= 0 or window_seconds <= 0:
            return 0
        now = time.time()
        cutoff = now - window_seconds
        member = f"{now:.6f}:{uuid.uuid4().hex}"
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {member: now})
        pipe.expire(key, window_seconds)
        _, count_before, _, _ = await pipe.execute()
        if int(count_before) >= limit:
            await self._redis.zrem(key, member)
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            retry_after = window_seconds
            if oldest:
                retry_after = max(1, int(window_seconds - (now - float(oldest[0][1]))))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limit_exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        return int(count_before) + 1


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _check_rate_limit(request: Request, key: str, limit: int) -> None:
    redis_client = getattr(request.app.state, "redis_client", None)
    if (settings.rate_limit_backend or "").strip().lower() == "redis" and redis_client is not None:
        limiter = RedisSlidingWindowRateLimiter(redis_client)
        await limiter.check(key, limit=limit, window_seconds=settings.auth_rate_limit_window_seconds)
        return
    auth_rate_limiter.check(
        key,
        limit=limit,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )


async def check_auth_rate_limit(request: Request, bucket: str, limit: int) -> None:
    ip = client_ip(request)
    await _check_rate_limit(request, f"{bucket}:{ip}", limit)


async def check_auth_subject_rate_limit(request: Request, bucket: str, subject: str, limit: int) -> None:
    ip = client_ip(request)
    normalized_subject = (subject or "").strip().lower() or "unknown"
    await _check_rate_limit(request, f"{bucket}:{ip}:{normalized_subject}", limit)
