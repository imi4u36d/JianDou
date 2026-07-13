"""Task query service - handles read-side queries for tasks.

Translates the Java TaskQueryService. Provides listing, detail, trace, logs,
status history, model calls, results, and materials queries.
"""

from __future__ import annotations

from typing import Any

from backend.config import settings
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_admin_query_service import TaskAdminQueryService
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_query_cache import TaskQueryCache
from backend.services.task_query_policy import (
    matches_task_status,
    showcase_comparator,
    task_comparator,
    task_type_set,
)
from backend.services.task_query_presenters import task_detail, task_list_item


class TaskQueryService:
    """Read-side query service for tasks.

    Mirrors the Java TaskQueryService, providing listing, detail, and
    sub-collection queries.
    """

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        cache: Any | None = None,
    ) -> None:
        self._task_repository: TaskRepository | None = task_repository
        self._execution_coordinator: TaskExecutionCoordinator = execution_coordinator or TaskExecutionCoordinator()
        self._query_cache = TaskQueryCache(cache)
        self._admin_queries = TaskAdminQueryService(
            repository=lambda: self.task_repository,
            coordinator=self._execution_coordinator,
            repo_method=self._repo_method,
            to_list_item=self._to_list_item,
            task_comparator=self._task_comparator,
            showcase_comparator=self._showcase_comparator,
            matches_status=self._matches_status,
        )

    @property
    def task_repository(self) -> TaskRepository:
        if self._task_repository is None:
            raise RuntimeError("TaskRepository not configured")
        return self._task_repository

    @task_repository.setter
    def task_repository(self, repo: TaskRepository) -> None:
        self._task_repository = repo

    def _repo_method(self, name: str) -> Any | None:
        if getattr(type(self.task_repository), name, None) is None:
            return None
        return getattr(self.task_repository, name)

    # ------------------------------------------------------------------
    # List tasks
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        owner_user_id: int,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """List tasks owned by the current user with filtering and sorting."""
        is_paginated = offset is not None or limit is not None
        page_offset = max(0, offset or 0)
        page_limit = max(1, limit or 10)
        list_task_summaries = self._repo_method("list_task_summaries")
        if list_task_summaries:
            cache_key = self._query_cache.task_list_key(
                owner_user_id,
                q,
                status,
                sort,
                task_type,
                exclude_task_type,
                page_offset if is_paginated else None,
                page_limit if is_paginated else None,
            )
            cached = await self._query_cache.get(cache_key)
            if isinstance(cached, (list, dict)):
                return cached
            items = await list_task_summaries(
                owner_user_id,
                q,
                status,
                sort,
                task_type=task_type,
                exclude_task_type=exclude_task_type,
                offset=page_offset if is_paginated else None,
                limit=page_limit if is_paginated else None,
            )
            if is_paginated:
                count_task_summaries = self._repo_method("count_task_summaries")
                total = (
                    await count_task_summaries(owner_user_id, q, status, task_type, exclude_task_type)
                    if count_task_summaries
                    else len(items)
                )
                result: dict[str, Any] = {
                    "items": items,
                    "total": total,
                    "offset": page_offset,
                    "limit": page_limit,
                }
                await self._query_cache.set(cache_key, result, settings.task_list_cache_ttl_seconds)
                return result
            await self._query_cache.set(cache_key, items, settings.task_list_cache_ttl_seconds)
            return items

        tasks = await self.task_repository.find_all()
        self._execution_coordinator.recompute_queue_positions(tasks)

        filtered = [t for t in tasks if t.owner_user_id == owner_user_id]

        # Apply text search
        if q and q.strip():
            q_lower = q.lower().strip()
            filtered = [
                t
                for t in filtered
                if q_lower in (t.title or "").lower() or q_lower in (t.creative_prompt or "").lower()
            ]

        # Apply status filter
        if status:
            filtered = [t for t in filtered if self._matches_status(t, status)]
        if task_type:
            allowed = task_type_set(task_type)
            filtered = [t for t in filtered if t.task_type in allowed]
        if exclude_task_type:
            excluded = task_type_set(exclude_task_type)
            filtered = [t for t in filtered if t.task_type not in excluded]

        # Sort
        filtered.sort(key=self._task_comparator(sort))

        total = len(filtered)
        if is_paginated:
            filtered = filtered[page_offset : page_offset + page_limit]
            return {
                "items": [self._to_list_item(t) for t in filtered],
                "total": total,
                "offset": page_offset,
                "limit": page_limit,
            }

        return [self._to_list_item(t) for t in filtered]

    async def admin_list_tasks(
        self,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        return await self._admin_queries.list_tasks(q, status, sort, offset, limit)

    async def showcase_cases(self) -> dict[str, Any]:
        return await self._admin_queries.showcase_cases()

    # ------------------------------------------------------------------
    # Get single task
    # ------------------------------------------------------------------

    async def get_task(self, task_id: str, owner_user_id: int) -> dict[str, Any]:
        """Get a single task by ID with owner check."""
        find_detail_light = self._repo_method("find_detail_light")
        if find_detail_light:
            detail = await find_detail_light(task_id, owner_user_id)
            if detail is None:
                raise ValueError(f"Task not found: {task_id}")
            return detail

        task = await self._require_owned_task(task_id, owner_user_id)
        self._execution_coordinator.recompute_queue_positions([task])
        return self._to_detail(task)

    async def admin_get_task(self, task_id: str) -> dict[str, Any]:
        """Get task detail without owner check (admin)."""
        find_detail_light = self._repo_method("find_detail_light")
        if find_detail_light:
            detail = await find_detail_light(task_id)
            if detail is None:
                raise ValueError(f"Task not found: {task_id}")
            return detail

        task = await self._require_task(task_id)
        self._execution_coordinator.recompute_queue_positions([task])
        return self._to_detail(task)

    # ------------------------------------------------------------------
    # Sub-collections
    # ------------------------------------------------------------------

    async def get_trace(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get trace events for a task."""
        get_task_trace = self._repo_method("get_task_trace")
        if get_task_trace:
            cache_key = self._query_cache.task_trace_key(owner_user_id, task_id, limit)
            cached = await self._query_cache.get(cache_key)
            if isinstance(cached, list):
                return cached
            trace = await get_task_trace(task_id, owner_user_id, limit)
            await self._query_cache.set(cache_key, trace, settings.task_trace_cache_ttl_seconds)
            return trace

        task = await self._require_owned_task(task_id, owner_user_id)
        if task.trace:
            return task.trace[-limit:]
        return []

    async def get_logs(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get log entries (same as trace for now)."""
        return await self.get_trace(task_id, owner_user_id, limit)

    async def get_status_history(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get status history for a task."""
        task = await self._require_owned_task(task_id, owner_user_id)
        if task.status_history:
            return task.status_history[-limit:]
        return []

    async def get_model_calls(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get model call records for a task."""
        task = await self._require_owned_task(task_id, owner_user_id)
        if task.model_calls:
            return task.model_calls[-limit:]
        return []

    async def get_results(self, task_id: str, owner_user_id: int) -> list[dict[str, Any]]:
        """Get task results (outputs)."""
        get_task_outputs_light = self._repo_method("get_task_outputs_light")
        if get_task_outputs_light:
            return await get_task_outputs_light(task_id, owner_user_id)
        task = await self._require_owned_task(task_id, owner_user_id)
        return list(task.outputs)

    async def get_materials(self, task_id: str, owner_user_id: int) -> list[dict[str, Any]]:
        """Get material assets for a task."""
        get_task_materials_light = self._repo_method("get_task_materials_light")
        if get_task_materials_light:
            return await get_task_materials_light(task_id, owner_user_id)
        task = await self._require_owned_task(task_id, owner_user_id)
        return list(task.materials)

    # ------------------------------------------------------------------
    # Admin queries
    # ------------------------------------------------------------------

    async def admin_overview(self) -> dict[str, Any]:
        return await self._admin_queries.overview()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _require_task(self, task_id: str) -> TaskRecord:
        task = await self.task_repository.find_by_id(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task

    async def _require_owned_task(self, task_id: str, owner_user_id: int) -> TaskRecord:
        task = await self._require_task(task_id)
        if task.owner_user_id != owner_user_id:
            raise ValueError(f"Task not found: {task_id}")
        return task

    def _to_list_item(self, task: TaskRecord) -> dict[str, Any]:
        return task_list_item(task)

    def _to_detail(self, task: TaskRecord) -> dict[str, Any]:
        return task_detail(task)

    async def invalidate_task_list_cache(self, owner_user_id: int | None = None) -> None:
        await self._query_cache.invalidate_task_lists(owner_user_id)

    @staticmethod
    def _task_comparator(sort: str | None):
        return task_comparator(sort)

    @staticmethod
    def _showcase_comparator():
        return showcase_comparator()

    @staticmethod
    def _matches_status(task: TaskRecord, status_filter: str | None) -> bool:
        return matches_task_status(task, status_filter)
