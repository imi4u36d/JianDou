from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import AttemptTriggerType
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_diagnosis_service import TaskQueueCoordinator
from backend.services.task_execution_coordinator import TaskExecutionCoordinator

pytestmark = pytest.mark.service


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


@pytest.mark.asyncio
async def test_repository_claim_next_marks_attempt_running_atomically(db_session) -> None:
    repository = TaskRepository(db_session)
    execution = TaskExecutionCoordinator()
    task = TaskRecord(
        id="task_claim_once",
        owner_user_id=7,
        task_type="image_generation",
        title="Claim once",
        status="PENDING",
        progress=0,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    await repository.save_mutation(execution.create_attempt(task, AttemptTriggerType.CREATE, {})["mutation"])
    await repository.save_mutation(execution.enqueue(task, "render", "task.created", "queued")["mutation"])

    assert await repository.claim_next_queued_task("worker_a") == task.id
    assert await repository.claim_next_queued_task("worker_b") is None

    loaded = await repository.find_by_id(task.id)
    assert loaded is not None
    attempt = loaded.attempts[0]
    assert attempt["status"] == "RUNNING"
    assert attempt["workerInstanceId"] == "worker_a"
    assert attempt["claimedAt"]
    assert attempt["queueLeftAt"]
    assert loaded.is_queued is False


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
