from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


class JsonCache:
    """Small JSON cache abstraction with a no-op fallback."""

    def __init__(self, redis_client: Any | None = None, enabled: bool = False) -> None:
        self._redis = redis_client
        self._enabled = enabled and redis_client is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        try:
            raw = await self._redis.get(key)
        except Exception as exc:
            logger.warning("Redis cache read failed for %s: %s", key, exc)
            return None
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self._enabled or ttl_seconds <= 0:
            return
        try:
            await self._redis.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Redis cache write failed for %s: %s", key, exc)

    async def delete_prefix(self, prefix: str) -> None:
        if not self._enabled:
            return
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*"):
                await self._redis.delete(key)
        except Exception as exc:
            logger.warning("Redis cache prefix delete failed for %s: %s", prefix, exc)

    async def close(self) -> None:
        if self._redis is None:
            return
        close = getattr(self._redis, "aclose", None)
        if callable(close):
            await close()


def create_redis_client() -> Any | None:
    if not settings.redis_url:
        return None
    try:
        from redis.asyncio import Redis

        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:
        logger.warning("Redis client initialization failed: %s", exc)
        return None


def create_json_cache(redis_client: Any | None) -> JsonCache:
    enabled = (settings.cache_backend or "").strip().lower() == "redis"
    return JsonCache(redis_client, enabled=enabled)
