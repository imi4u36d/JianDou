"""Administrative and public showcase task read models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.shared import string_value


class TaskAdminQueryService:
    """Build admin list/overview and public showcase responses."""

    SHOWCASE_LIMIT = 8

    def __init__(
        self,
        repository: Callable[[], TaskRepository],
        coordinator: TaskExecutionCoordinator,
        repo_method: Callable[[str], Any | None],
        to_list_item: Callable[[TaskRecord], dict[str, Any]],
        task_comparator: Callable[[str | None], Any],
        showcase_comparator: Callable[[], Any],
        matches_status: Callable[[TaskRecord, str | None], bool],
    ) -> None:
        self._repository = repository
        self._coordinator = coordinator
        self._repo_method = repo_method
        self._to_list_item = to_list_item
        self._task_comparator = task_comparator
        self._showcase_comparator = showcase_comparator
        self._matches_status = matches_status

    async def list_tasks(
        self,
        q: str | None,
        status: str | None,
        sort: str | None,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        list_summaries = self._repo_method("list_task_summaries")
        if list_summaries:
            items = await list_summaries(None, q, status, sort, offset=offset, limit=limit)
            count_summaries = self._repo_method("count_task_summaries")
            total = await count_summaries(None, q, status) if count_summaries else len(items)
            return {"items": items, "total": total, "offset": offset, "limit": limit}

        tasks = await self._all_tasks()
        filtered = list(tasks)
        if q and q.strip():
            query = q.lower().strip()
            filtered = [
                task
                for task in filtered
                if query in (task.title or "").lower()
                or query in (task.creative_prompt or "").lower()
                or query in (task.source_file_name or "").lower()
            ]
        if status:
            filtered = [task for task in filtered if self._matches_status(task, status)]
        filtered.sort(key=self._task_comparator(sort))
        return {
            "items": [self._to_list_item(task) for task in filtered[offset : offset + limit]],
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
        }

    async def showcase_cases(self) -> dict[str, Any]:
        tasks = await self._all_tasks()
        eligible = [
            task
            for task in tasks
            if task.status == "COMPLETED" and (task.completed_output_count > 0 or task.outputs)
        ]
        eligible.sort(key=self._showcase_comparator())
        items = []
        for task in eligible[: self.SHOWCASE_LIMIT]:
            preview_url = next(
                (
                    string_value(output.get("previewUrl", output.get("remoteUrl", "")))
                    for output in task.outputs
                    if string_value(output.get("previewUrl", output.get("remoteUrl", "")))
                ),
                "",
            )
            if not preview_url:
                continue
            items.append(
                {
                    "taskId": task.id,
                    "title": task.title,
                    "taskType": task.task_type,
                    "aspectRatio": task.aspect_ratio,
                    "effectRating": task.effect_rating,
                    "previewUrl": preview_url,
                    "completedOutputCount": task.completed_output_count,
                    "updatedAt": task.updated_at,
                }
            )
        return {
            "generatedAt": TaskRecord.now_iso(),
            "totalCompletedTasks": sum(1 for task in tasks if task.status == "COMPLETED"),
            "items": items,
        }

    async def overview(self) -> dict[str, Any]:
        overview_snapshot = self._repo_method("admin_overview_snapshot")
        if overview_snapshot:
            snapshot = await overview_snapshot()
            queue_snapshot = snapshot["queueSnapshot"]
            return self._overview_response(
                counts=snapshot["counts"],
                queue_snapshot=queue_snapshot,
                recent_tasks=snapshot["recentTasks"],
                recent_failures=snapshot["recentFailures"],
                recent_running=snapshot["recentRunningTasks"],
            )

        queue_snapshot = self._coordinator.queue_snapshot()
        tasks = await self._all_tasks()
        tasks.sort(key=lambda task: string_value(task.created_at), reverse=True)
        total = len(tasks)
        recent_failures = [task for task in tasks if task.status == "FAILED"][:6]
        recent_running = [task for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}][:6]
        running_count = sum(
            1 for task in tasks if task.status in {"ANALYZING", "PLANNING", "RENDERING"}
        )
        counts = {
            "totalTasks": total,
            "queuedTasks": len(queue_snapshot),
            "runningTasks": running_count,
            "completedTasks": sum(1 for task in tasks if task.status == "COMPLETED"),
            "failedTasks": sum(1 for task in tasks if task.status == "FAILED"),
            "highRiskTasks": 0,
            "riskyTasks": 0,
            "semanticTasks": sum(1 for task in tasks if task.has_transcript),
            "timedSemanticTasks": sum(1 for task in tasks if task.has_timed_transcript),
            "averageProgress": sum(task.progress for task in tasks) // total if total else 0,
            "totalUsers": 0,
            "activeUsers": 0,
            "adminUsers": 0,
            "disabledUsers": 0,
        }
        return self._overview_response(
            counts=counts,
            queue_snapshot=queue_snapshot,
            recent_tasks=[self._to_list_item(task) for task in tasks[:8]],
            recent_failures=[self._to_list_item(task) for task in recent_failures],
            recent_running=[self._to_list_item(task) for task in recent_running],
        )

    def _overview_response(
        self,
        counts: dict[str, int],
        queue_snapshot: list[str],
        recent_tasks: list[dict[str, Any]],
        recent_failures: list[dict[str, Any]],
        recent_running: list[dict[str, Any]],
    ) -> dict[str, Any]:
        generated_at = TaskRecord.now_iso()
        return {
            "generatedAt": generated_at,
            "counts": counts,
            "queue": {
                "generatedAt": generated_at,
                "queueLength": counts["queuedTasks"],
                "queueSnapshot": queue_snapshot,
                "runningWorkers": 0,
                "userQueues": [],
                "latestEvents": [],
                "oldestQueuedTaskId": queue_snapshot[0] if queue_snapshot else "",
                "oldestQueuedTaskTitle": "",
                "oldestQueuedTaskCreatedAt": None,
            },
            "workers": {"items": [], "onlineCount": 0},
            "recentTasks": recent_tasks,
            "recentFailures": recent_failures,
            "recentRunningTasks": recent_running,
            "recentTraceCount": 0,
        }

    async def _all_tasks(self) -> list[TaskRecord]:
        tasks = await self._repository().find_all()
        self._coordinator.recompute_queue_positions(tasks)
        return tasks
