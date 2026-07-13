"""Cache protocol adapter and key policy for task queries."""

from __future__ import annotations

from typing import Any

from backend.shared import string_value


class TaskQueryCache:
    def __init__(self, cache: Any | None) -> None:
        self._cache = cache

    async def get(self, key: str) -> Any | None:
        return None if self._cache is None else await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._cache is not None:
            await self._cache.set(key, value, ttl_seconds)

    async def invalidate_task_lists(self, owner_user_id: int | None = None) -> None:
        if self._cache is None:
            return
        prefix = "task:list:" if owner_user_id is None else f"task:list:{owner_user_id}:"
        await self._cache.delete_prefix(prefix)

    @staticmethod
    def task_list_key(
        owner_user_id: int,
        q: str | None,
        status: str | None,
        sort: str | None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> str:
        normalized = (string_value(value).strip().lower() for value in (q, status, sort, task_type, exclude_task_type))
        return ":".join(
            [
                "task",
                "list",
                str(owner_user_id),
                *normalized,
                str(offset) if offset is not None else "all",
                str(limit) if limit is not None else "all",
            ]
        )

    @staticmethod
    def task_trace_key(owner_user_id: int, task_id: str, limit: int) -> str:
        return f"task:trace:{owner_user_id}:{task_id}:{limit}"
