from __future__ import annotations

import pytest
pytestmark = pytest.mark.service
from typing import Any

import pytest

from backend.domain.task_record import TaskRecord
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_query_service import TaskQueryService


def _task(
    task_id: str,
    owner_user_id: int,
    title: str,
    status: str,
    updated_at: str,
    progress: int = 0,
) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=owner_user_id,
        task_type="video_generation",
        title=title,
        status=status,
        progress=progress,
        created_at=updated_at,
        updated_at=updated_at,
        aspect_ratio="16:9",
        min_duration_seconds=5,
        max_duration_seconds=10,
        creative_prompt=f"{title} prompt",
    )


@pytest.mark.asyncio
async def test_list_tasks_filters_owner_search_status_and_queue_position() -> None:
    owner_task = _task("task_owner", 1, "Ocean launch", "PENDING", "2026-01-01T00:01:00+00:00")
    other_owner_task = _task("task_other", 2, "Ocean launch private", "PENDING", "2026-01-01T00:02:00+00:00")
    completed_task = _task("task_done", 1, "Forest clip", "COMPLETED", "2026-01-01T00:03:00+00:00")
    coordinator = TaskExecutionCoordinator()
    coordinator.task_queue_port.enqueue(owner_task.id)
    coordinator.task_queue_port.enqueue(other_owner_task.id)
    service = TaskQueryService(_TaskQueryRepository([owner_task, other_owner_task, completed_task]), coordinator)

    items = await service.list_tasks(owner_user_id=1, q="ocean", status="queued", sort="updated_desc")

    assert [item["id"] for item in items] == ["task_owner"]
    assert items[0]["isQueued"] is True
    assert items[0]["queuePosition"] == 1


@pytest.mark.asyncio
async def test_admin_list_tasks_includes_all_owners_and_sorts_by_progress() -> None:
    low = _task("task_low", 1, "Low", "RENDERING", "2026-01-01T00:01:00+00:00", progress=10)
    high = _task("task_high", 2, "High", "RENDERING", "2026-01-01T00:02:00+00:00", progress=90)
    completed = _task("task_done", 3, "Done", "COMPLETED", "2026-01-01T00:03:00+00:00", progress=100)
    service = TaskQueryService(_TaskQueryRepository([low, high, completed]), TaskExecutionCoordinator())

    result = await service.admin_list_tasks(status="rendering", sort="progress_desc")
    items = result["items"]

    assert result["total"] == 2
    assert [item["id"] for item in items] == ["task_high", "task_low"]
    assert [item["ownerUserId"] for item in items] == [2, 1]


@pytest.mark.asyncio
async def test_get_task_enforces_owner_boundary() -> None:
    task = _task("task_private", 1, "Private", "PENDING", "2026-01-01T00:01:00+00:00")
    service = TaskQueryService(_TaskQueryRepository([task]), TaskExecutionCoordinator())

    with pytest.raises(ValueError, match="Task not found: task_private"):
        await service.get_task("task_private", owner_user_id=2)


@pytest.mark.asyncio
async def test_showcase_cases_returns_completed_tasks_with_preview() -> None:
    hidden = _task("task_hidden", 1, "Hidden", "COMPLETED", "2026-01-01T00:01:00+00:00")
    hidden.completed_output_count = 1
    shown = _task("task_shown", 1, "Shown", "COMPLETED", "2026-01-01T00:02:00+00:00")
    shown.completed_output_count = 1
    shown.effect_rating = 5
    shown.outputs.append({"previewUrl": "https://example.test/video.mp4"})
    failed = _task("task_failed", 1, "Failed", "FAILED", "2026-01-01T00:03:00+00:00")
    service = TaskQueryService(_TaskQueryRepository([hidden, shown, failed]), TaskExecutionCoordinator())

    showcase = await service.showcase_cases()

    assert showcase["totalCompletedTasks"] == 2
    assert showcase["items"] == [
        {
            "taskId": "task_shown",
            "title": "Shown",
            "taskType": "video_generation",
            "aspectRatio": "16:9",
            "effectRating": 5,
            "previewUrl": "https://example.test/video.mp4",
            "completedOutputCount": 1,
            "updatedAt": "2026-01-01T00:02:00+00:00",
        }
    ]


class _TaskQueryRepository:
    def __init__(self, tasks: list[TaskRecord]) -> None:
        self.tasks = tasks

    async def find_all(self) -> list[TaskRecord]:
        return list(self.tasks)

    async def find_by_id(self, task_id: str) -> TaskRecord | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected repository call: {name}")
