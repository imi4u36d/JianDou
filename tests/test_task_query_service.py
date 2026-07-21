from __future__ import annotations

from typing import Any

import pytest

from backend.domain.task_record import TaskRecord
from backend.schemas.admin import AdminOverviewResponse
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_query_service import TaskQueryService

pytestmark = pytest.mark.service


def _task(
    task_id: str,
    owner_user_id: int,
    title: str,
    status: str,
    updated_at: str,
    progress: int = 0,
    created_at: str | None = None,
) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=owner_user_id,
        task_type="video_generation",
        title=title,
        status=status,
        progress=progress,
        created_at=created_at or updated_at,
        updated_at=updated_at,
        aspect_ratio="16:9",
        min_duration_seconds=5,
        max_duration_seconds=10,
        creative_prompt=f"{title} prompt",
    )


@pytest.mark.asyncio
async def test_list_tasks_default_sort_uses_created_time_not_updated_time() -> None:
    old_but_updated = _task(
        "task_old_but_updated",
        1,
        "Old",
        "PENDING",
        "2026-01-03T00:00:00+00:00",
        created_at="2026-01-01T00:00:00+00:00",
    )
    newly_created = _task(
        "task_newly_created",
        1,
        "New",
        "PENDING",
        "2026-01-02T00:00:00+00:00",
        created_at="2026-01-02T00:00:00+00:00",
    )
    service = TaskQueryService(_TaskQueryRepository([old_but_updated, newly_created]), TaskExecutionCoordinator())

    default_items = await service.list_tasks(owner_user_id=1)
    updated_items = await service.list_tasks(owner_user_id=1, sort="updated_desc")

    assert [item["id"] for item in default_items] == ["task_newly_created", "task_old_but_updated"]
    assert [item["id"] for item in updated_items] == ["task_old_but_updated", "task_newly_created"]


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
async def test_list_tasks_paginated_delegates_offset_limit_to_repository() -> None:
    repo = _TaskSummaryRepository(
        [
            {"id": f"task_{index:02d}", "ownerUserId": 1, "title": f"Task {index:02d}"}
            for index in range(25)
        ]
    )
    service = TaskQueryService(repo, TaskExecutionCoordinator())

    result = await service.list_tasks(owner_user_id=1, sort="created_desc", offset=10, limit=10)

    assert result["total"] == 25
    assert result["offset"] == 10
    assert result["limit"] == 10
    assert [item["id"] for item in result["items"]] == [f"task_{index:02d}" for index in range(10, 20)]
    assert repo.list_calls == [
        {
            "owner_user_id": 1,
            "q": None,
            "status": None,
            "sort": "created_desc",
            "task_type": None,
            "exclude_task_type": None,
            "offset": 10,
            "limit": 10,
        }
    ]
    assert repo.count_calls == [{"owner_user_id": 1, "q": None, "status": None, "task_type": None, "exclude_task_type": None}]


@pytest.mark.asyncio
async def test_get_task_enforces_owner_boundary() -> None:
    task = _task("task_private", 1, "Private", "PENDING", "2026-01-01T00:01:00+00:00")
    service = TaskQueryService(_TaskQueryRepository([task]), TaskExecutionCoordinator())

    with pytest.raises(ValueError, match="Task not found: task_private"):
        await service.get_task("task_private", owner_user_id=2)


@pytest.mark.asyncio
async def test_admin_overview_builds_counts_and_recent_groups() -> None:
    running = _task("task_running", 1, "Running", "RENDERING", "2026-01-02T00:00:00+00:00", 50)
    failed = _task("task_failed", 2, "Failed", "FAILED", "2026-01-03T00:00:00+00:00", 20)
    completed = _task("task_done", 3, "Done", "COMPLETED", "2026-01-01T00:00:00+00:00", 100)
    service = TaskQueryService(
        _TaskQueryRepository([running, failed, completed]),
        TaskExecutionCoordinator(),
    )

    overview = await service.admin_overview()

    assert overview["counts"]["totalTasks"] == 3
    assert overview["counts"]["runningTasks"] == 1
    assert overview["counts"]["failedTasks"] == 1
    assert [item["id"] for item in overview["recentFailures"]] == ["task_failed"]
    assert [item["id"] for item in overview["recentRunningTasks"]] == ["task_running"]


@pytest.mark.asyncio
async def test_admin_overview_prefers_lightweight_repository_snapshot() -> None:
    repository = _AdminOverviewRepository()
    service = TaskQueryService(repository, TaskExecutionCoordinator())

    overview = await service.admin_overview()

    assert overview["counts"]["totalTasks"] == 42
    assert overview["queue"]["queueSnapshot"] == ["task_queued"]
    assert repository.snapshot_calls == 1


def test_admin_overview_response_preserves_nested_camel_case_contract() -> None:
    payload = {
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "counts": {"totalTasks": 1},
        "queue": {"queueLength": 0},
        "workers": {"onlineCount": 0},
        "recentTasks": [{"id": "task_1"}],
        "modelReady": True,
    }

    response = AdminOverviewResponse.model_validate(payload).model_dump(by_alias=True)

    assert response["counts"] == {"totalTasks": 1}
    assert response["recentTasks"] == [{"id": "task_1"}]
    assert response["modelReady"] is True


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


class _AdminOverviewRepository:
    def __init__(self) -> None:
        self.snapshot_calls = 0

    async def admin_overview_snapshot(self) -> dict[str, Any]:
        self.snapshot_calls += 1
        return {
            "counts": {
                "totalTasks": 42,
                "queuedTasks": 1,
                "runningTasks": 0,
                "completedTasks": 0,
                "failedTasks": 0,
                "highRiskTasks": 0,
                "riskyTasks": 0,
                "semanticTasks": 0,
                "timedSemanticTasks": 0,
                "averageProgress": 0,
                "totalUsers": 2,
                "activeUsers": 2,
                "adminUsers": 1,
                "disabledUsers": 0,
            },
            "queueSnapshot": ["task_queued"],
            "recentTasks": [],
            "recentFailures": [],
            "recentRunningTasks": [],
        }

    async def find_all(self) -> list[TaskRecord]:
        raise AssertionError("overview must not load full task aggregates")


class _TaskSummaryRepository:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.list_calls: list[dict[str, Any]] = []
        self.count_calls: list[dict[str, Any]] = []

    async def list_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self.list_calls.append(
            {
                "owner_user_id": owner_user_id,
                "q": q,
                "status": status,
                "sort": sort,
                "task_type": task_type,
                "exclude_task_type": exclude_task_type,
                "offset": offset,
                "limit": limit,
            }
        )
        start = offset or 0
        end = start + limit if limit is not None else None
        return self.items[start:end]

    async def count_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
    ) -> int:
        self.count_calls.append({
            "owner_user_id": owner_user_id,
            "q": q,
            "status": status,
            "task_type": task_type,
            "exclude_task_type": exclude_task_type,
        })
        return len(self.items)
