"""Task query service - handles read-side queries for tasks.

Translates the Java TaskQueryService. Provides listing, detail, trace, logs,
status history, model calls, results, and materials queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.config import settings
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.shared import string_value


def _trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    v = value.strip()
    return v if v else fallback


def _timestamp(value: str | None) -> float:
    text = string_value(value).strip()
    if not text:
        return 0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


class TaskQueryService:
    """Read-side query service for tasks.

    Mirrors the Java TaskQueryService, providing listing, detail, and
    sub-collection queries.
    """

    SHOWCASE_LIMIT = 8

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        cache: Any | None = None,
    ) -> None:
        self._task_repository: TaskRepository | None = task_repository
        self._execution_coordinator: TaskExecutionCoordinator = (
            execution_coordinator or TaskExecutionCoordinator()
        )
        self._cache = cache

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
    ) -> list[dict[str, Any]]:
        """List tasks owned by the current user with filtering and sorting."""
        list_task_summaries = self._repo_method("list_task_summaries")
        if list_task_summaries:
            cache_key = self._task_list_cache_key(owner_user_id, q, status, sort)
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                return cached
            items = await list_task_summaries(owner_user_id, q, status, sort)
            await self._cache_set(cache_key, items, settings.task_list_cache_ttl_seconds)
            return items

        tasks = await self.task_repository.find_all()
        self._execution_coordinator.recompute_queue_positions(tasks)

        filtered = [
            t for t in tasks
            if t.owner_user_id == owner_user_id
        ]

        # Apply text search
        if q and q.strip():
            q_lower = q.lower().strip()
            filtered = [
                t for t in filtered
                if q_lower in (t.title or "").lower()
                or q_lower in (t.creative_prompt or "").lower()
            ]

        # Apply status filter
        if status:
            filtered = [
                t for t in filtered
                if self._matches_status(t, status)
            ]

        # Sort
        filtered.sort(key=self._task_comparator(sort))

        return [self._to_list_item(t) for t in filtered]

    async def admin_list_tasks(
        self,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List tasks for admin with pagination."""
        list_task_summaries = self._repo_method("list_task_summaries")
        if list_task_summaries:
            items = await list_task_summaries(None, q, status, sort)
            return {
                "items": items[offset : offset + limit],
                "total": len(items),
                "offset": offset,
                "limit": limit,
            }

        tasks = await self.task_repository.find_all()
        self._execution_coordinator.recompute_queue_positions(tasks)

        filtered = list(tasks)

        # Apply text search
        if q and q.strip():
            q_lower = q.lower().strip()
            filtered = [
                t for t in filtered
                if q_lower in (t.title or "").lower()
                or q_lower in (t.creative_prompt or "").lower()
                or q_lower in (t.source_file_name or "").lower()
            ]

        # Apply status filter
        if status:
            filtered = [
                t for t in filtered
                if self._matches_status(t, status)
            ]

        # Sort
        filtered.sort(key=self._task_comparator(sort))

        total = len(filtered)
        page_items = filtered[offset : offset + limit]
        return {
            "items": [self._to_list_item(t) for t in page_items],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def showcase_cases(self) -> dict[str, Any]:
        """Return public showcase data: completed tasks with preview results."""
        tasks = await self.task_repository.find_all()
        self._execution_coordinator.recompute_queue_positions(tasks)

        eligible = [
            t for t in tasks
            if t.status == "COMPLETED"
            and (t.completed_output_count > 0 or t.outputs)
        ]

        eligible.sort(key=self._showcase_comparator())

        items = []
        for t in eligible[:self.SHOWCASE_LIMIT]:
            preview_url = ""
            for output in t.outputs:
                preview_url = string_value(output.get("previewUrl", output.get("remoteUrl", "")))
                if preview_url:
                    break
            if not preview_url:
                continue
            items.append({
                "taskId": t.id,
                "title": t.title,
                "taskType": t.task_type,
                "aspectRatio": t.aspect_ratio,
                "effectRating": t.effect_rating,
                "previewUrl": preview_url,
                "completedOutputCount": t.completed_output_count,
                "updatedAt": t.updated_at,
            })

        total_completed = sum(1 for t in tasks if t.status == "COMPLETED")

        return {
            "generatedAt": TaskRecord.now_iso(),
            "totalCompletedTasks": total_completed,
            "items": items,
        }

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
            cache_key = self._task_trace_cache_key(owner_user_id, task_id, limit)
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                return cached
            trace = await get_task_trace(task_id, owner_user_id, limit)
            await self._cache_set(cache_key, trace, settings.task_trace_cache_ttl_seconds)
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
        """Admin dashboard overview."""
        queue_snapshot = self._execution_coordinator.queue_snapshot()
        tasks = await self.task_repository.find_all()
        self._execution_coordinator.recompute_queue_positions(tasks)
        tasks.sort(key=lambda t: string_value(t.created_at), reverse=True)

        total = len(tasks)
        list_items = [self._to_list_item(t) for t in tasks]
        recent_tasks = list_items[:8]

        recent_failures = [t for t in tasks if t.status == "FAILED"][:6]
        recent_running = [t for t in tasks if t.status in ("ANALYZING", "PLANNING", "RENDERING")][:6]

        running_count = sum(1 for t in tasks if t.status in ("ANALYZING", "PLANNING", "RENDERING"))
        completed_count = sum(1 for t in tasks if t.status == "COMPLETED")
        failed_count = sum(1 for t in tasks if t.status == "FAILED")
        semantic_count = sum(1 for t in tasks if t.has_transcript)
        timed_semantic_count = sum(1 for t in tasks if t.has_timed_transcript)
        avg_progress = sum(t.progress for t in tasks) // total if total > 0 else 0

        return {
            "generatedAt": TaskRecord.now_iso(),
            "counts": {
                "totalTasks": total,
                "queuedTasks": len(queue_snapshot),
                "runningTasks": running_count,
                "completedTasks": completed_count,
                "failedTasks": failed_count,
                "highRiskTasks": 0,
                "riskyTasks": 0,
                "semanticTasks": semantic_count,
                "timedSemanticTasks": timed_semantic_count,
                "averageProgress": avg_progress,
            },
            "queue": {
                "generatedAt": TaskRecord.now_iso(),
                "queueLength": len(queue_snapshot),
                "queueSnapshot": queue_snapshot,
                "runningWorkers": 0,
                "userQueues": [],
                "latestEvents": [],
                "oldestQueuedTaskId": queue_snapshot[0] if queue_snapshot else "",
                "oldestQueuedTaskTitle": "",
                "oldestQueuedTaskCreatedAt": None,
            },
            "workers": {
                "items": [],
                "onlineCount": 0,
            },
            "recentTasks": recent_tasks,
            "recentFailures": [self._to_list_item(t) for t in recent_failures],
            "recentRunningTasks": [self._to_list_item(t) for t in recent_running],
            "recentTraceCount": 0,
        }

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
        """Build a list-item response dict from a TaskRecord."""
        current_stage = ""
        active_worker = ""
        for attempt in task.attempts:
            if attempt.get("attemptId") == task.active_attempt_id:
                current_stage = string_value(attempt.get("resumeFromStage", ""))
                active_worker = string_value(attempt.get("workerInstanceId", ""))
                break

        return {
            "id": task.id,
            "taskType": task.task_type,
            "title": task.title,
            "status": task.status,
            "progress": task.progress,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "retryCount": task.retry_count,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "effectRatingNote": task.effect_rating_note,
            "ratedAt": task.rated_at,
            "hasTranscript": task.has_transcript,
            "hasTimedTranscript": task.has_timed_transcript,
            "sourceAssetCount": task.source_asset_count,
            "editingMode": task.editing_mode,
            "isQueued": task.is_queued,
            "queuePosition": task.queue_position,
            "currentStage": current_stage,
            "activeWorkerInstanceId": active_worker,
            "plannedClipCount": 0,
            "renderedClipCount": 0,
            "diagnosisSeverity": "",
            "diagnosisCode": "",
            "diagnosisHint": "",
            "recommendedAction": "",
            "failureReason": task.error_message or "",
            "failureStage": "",
            "failureClipIndex": None,
            "thumbnailUrl": "",
            "ownerUserId": task.owner_user_id,
            "ownerUsername": "",
            "ownerRole": "",
        }

    def _to_detail(self, task: TaskRecord) -> dict[str, Any]:
        """Build a detail response dict from a TaskRecord."""
        current_stage = ""
        active_worker = ""
        for attempt in task.attempts:
            if attempt.get("attemptId") == task.active_attempt_id:
                current_stage = string_value(attempt.get("resumeFromStage", ""))
                active_worker = string_value(attempt.get("workerInstanceId", ""))
                break

        return {
            "id": task.id,
            "taskType": task.task_type,
            "title": task.title,
            "status": task.status,
            "progress": task.progress,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
            "sourceFileName": task.source_file_name,
            "aspectRatio": task.aspect_ratio,
            "minDurationSeconds": task.min_duration_seconds,
            "maxDurationSeconds": task.max_duration_seconds,
            "retryCount": task.retry_count,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "completedOutputCount": task.completed_output_count,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "effectRatingNote": task.effect_rating_note,
            "ratedAt": task.rated_at,
            "isQueued": task.is_queued,
            "queuePosition": task.queue_position,
            "currentStage": current_stage,
            "activeWorkerInstanceId": active_worker,
            "ownerUserId": task.owner_user_id,
            "ownerUsername": "",
            "errorMessage": task.error_message or "",
            "editingMode": task.editing_mode,
            "creativePrompt": task.creative_prompt,
            "hasTranscript": task.has_transcript,
            "hasTimedTranscript": task.has_timed_transcript,
            "sourceAssetCount": task.source_asset_count,
            "transcriptPreview": task.transcript_text[: min(220, len(task.transcript_text))]
            if task.transcript_text
            else None,
            "transcriptCueCount": 0,
            "executionContext": task.execution_context,
            "requestSnapshot": task.request_snapshot or {},
            "storyboardScript": task.storyboard_script,
            "artifactDirectories": {},
            "durationDiagnostics": [],
            "plan": [],
            "trace": list(task.trace),
            "statusHistory": list(task.status_history),
            "attempts": list(task.attempts),
            "stageRuns": list(task.stage_runs),
            "modelCalls": list(task.model_calls),
            "materials": list(task.materials),
            "outputs": list(task.outputs),
            "sourceAssets": list(task.source_assets),
        }

    async def invalidate_task_list_cache(self, owner_user_id: int | None = None) -> None:
        if not self._cache:
            return
        if owner_user_id is None:
            await self._cache.delete_prefix("task:list:")
            return
        await self._cache.delete_prefix(f"task:list:{owner_user_id}:")

    async def _cache_get(self, key: str) -> Any | None:
        if not self._cache:
            return None
        return await self._cache.get(key)

    async def _cache_set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self._cache:
            return
        await self._cache.set(key, value, ttl_seconds)

    @staticmethod
    def _task_list_cache_key(owner_user_id: int, q: str | None, status: str | None, sort: str | None) -> str:
        return (
            f"task:list:{owner_user_id}:"
            f"{string_value(q).strip().lower()}:"
            f"{string_value(status).strip().lower()}:"
            f"{string_value(sort).strip().lower()}"
        )

    @staticmethod
    def _task_trace_cache_key(owner_user_id: int, task_id: str, limit: int) -> str:
        return f"task:trace:{owner_user_id}:{task_id}:{limit}"

    @staticmethod
    def _task_comparator(sort: str | None):
        """Return a sort key function based on the sort parameter."""
        normalized = _trimmed(sort, "created_desc").lower()

        def sort_key(task: TaskRecord):
            if normalized == "created_desc":
                return (-_timestamp(task.created_at), string_value(task.id))
            if normalized == "progress_desc":
                return (-task.progress, -_timestamp(task.updated_at), string_value(task.id))
            if normalized == "semantic_desc":
                score = 1 if task.has_timed_transcript or task.has_transcript else 0
                return (-score, -_timestamp(task.updated_at), string_value(task.id))
            if normalized == "status_desc":
                return (0, string_value(task.status), -_timestamp(task.updated_at), string_value(task.id))
            if normalized in ("effect_rating_desc", "rating_desc"):
                rating = task.effect_rating if task.effect_rating is not None else float("-inf")
                return (-rating, -_timestamp(task.updated_at), string_value(task.id))
            return (-_timestamp(task.updated_at), string_value(task.id))

        return lambda t: (sort_key(t),)

    @staticmethod
    def _showcase_comparator():
        """Return a sort key function for showcase items."""
        def sort_key(task: TaskRecord):
            rating = task.effect_rating if task.effect_rating is not None else float("-inf")
            return (-rating, -task.completed_output_count, string_value(task.updated_at))
        return sort_key

    @staticmethod
    def _matches_status(task: TaskRecord, status_filter: str | None) -> bool:
        """Check if task matches the status filter."""
        if not status_filter:
            return True
        normalized = status_filter.strip().upper()
        if normalized == "QUEUED":
            return task.is_queued
        return task.status == normalized
