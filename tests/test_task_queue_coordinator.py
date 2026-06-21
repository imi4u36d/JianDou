from __future__ import annotations

import pytest
pytestmark = pytest.mark.service
from typing import Any

import pytest

from backend.services.task_diagnosis_service import TaskQueueCoordinator


@pytest.mark.asyncio
async def test_task_queue_coordinator_delegates_worker_side_operations() -> None:
    repository = _RecordingTaskRepository(
        queued_task_ids=["task_a", "task_b"],
        claim_result="task_a",
    )
    coordinator = TaskQueueCoordinator(repository)

    assert await coordinator.snapshot() == ["task_a", "task_b"]
    assert await coordinator.claim_next("worker_1") == "task_a"
    await coordinator.remove("task_a")

    assert repository.calls == [
        ("list_queued_task_ids", 500),
        ("claim_next_queued_task", "worker_1"),
        ("remove_queued_task", "task_a"),
    ]


def test_task_queue_coordinator_does_not_expose_silent_enqueue() -> None:
    coordinator = TaskQueueCoordinator(_RecordingTaskRepository())

    assert not hasattr(coordinator, "enqueue")


class _RecordingTaskRepository:
    def __init__(
        self,
        queued_task_ids: list[str] | None = None,
        claim_result: str | None = None,
    ) -> None:
        self._queued_task_ids = queued_task_ids or []
        self._claim_result = claim_result
        self.calls: list[tuple[str, Any]] = []

    async def list_queued_task_ids(self, limit: int) -> list[str]:
        self.calls.append(("list_queued_task_ids", limit))
        return self._queued_task_ids

    async def claim_next_queued_task(self, worker_instance_id: str) -> str | None:
        self.calls.append(("claim_next_queued_task", worker_instance_id))
        return self._claim_result

    async def remove_queued_task(self, task_id: str) -> None:
        self.calls.append(("remove_queued_task", task_id))
