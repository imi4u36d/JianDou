from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.domain.enums import AttemptStatus, AttemptTriggerType, QueueEventType, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_execution_coordinator import (
    TaskExecutionCoordinator,
    TaskStateTransition,
)


def _task(task_id: str = "task_1", status: str = "PENDING") -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=1,
        title="Task",
        status=status,
        progress=0,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _active_attempt(task: TaskRecord) -> dict[str, Any]:
    return next(row for row in task.attempts if row["attemptId"] == task.active_attempt_id)


def test_attempt_lifecycle_emits_queue_events() -> None:
    coordinator = TaskExecutionCoordinator()
    task = _task()

    create_result = coordinator.create_attempt(
        task,
        AttemptTriggerType.CREATE,
        {"resumeFromStage": "storyboard", "resumeFromClipIndex": 2},
    )

    attempt = create_result["attempt"]
    assert task.active_attempt_id == attempt["attemptId"]
    assert attempt["attemptNo"] == 1
    assert attempt["triggerType"] == AttemptTriggerType.CREATE.value
    assert attempt["status"] == AttemptStatus.CREATED.value
    assert attempt["resumeFromStage"] == "storyboard"
    assert attempt["resumeFromClipIndex"] == 2
    assert create_result["mutation"].attempts == [attempt]

    enqueue_result = coordinator.enqueue(task, "dispatch", "task.enqueued", "Task enqueued.")
    queued_attempt = _active_attempt(task)

    assert task.status == "PENDING"
    assert task.is_queued is True
    assert coordinator.queue_snapshot() == [task.id]
    assert queued_attempt["status"] == AttemptStatus.QUEUED.value
    assert queued_attempt["workerInstanceId"] == ""
    assert enqueue_result["queue_event"]["eventType"] == QueueEventType.ENQUEUED.value
    assert enqueue_result["mutation"].queue_event_rows == [enqueue_result["queue_event"]]

    running_result = coordinator.mark_active_attempt_running(task, "worker_1")
    running_attempt = _active_attempt(task)

    assert running_result is not None
    assert running_attempt["status"] == AttemptStatus.RUNNING.value
    assert running_attempt["workerInstanceId"] == "worker_1"
    assert running_attempt["queueLeftAt"] is not None
    assert running_result["queue_event"]["eventType"] == QueueEventType.CLAIMED.value
    assert running_result["queue_event"]["workerInstanceId"] == "worker_1"

    finished_result = coordinator.mark_active_attempt_finished(task, AttemptStatus.FINISHED)
    finished_attempt = _active_attempt(task)

    assert finished_result is not None
    assert finished_attempt["status"] == AttemptStatus.FINISHED.value
    assert finished_attempt["finishedAt"] is not None
    assert finished_result["queue_event"]["eventType"] == QueueEventType.COMPLETED.value


def test_transition_task_updates_terminal_state_and_attempt() -> None:
    coordinator = TaskExecutionCoordinator()
    task = _task(status="RENDERING")
    coordinator.create_attempt(task, AttemptTriggerType.CREATE, {})
    coordinator.mark_active_attempt_running(task, "worker_1")

    result = coordinator.transition_task(
        task,
        TaskStateTransition.error(
            "FAILED",
            100,
            "render",
            "task.failed",
            "Render failed.",
        ).with_attempt(AttemptStatus.FAILED, "provider timeout"),
    )

    attempt = _active_attempt(task)
    mutation = result["mutation"]

    assert task.status == "FAILED"
    assert task.progress == 100
    assert task.error_message == "provider timeout"
    assert task.finished_at is not None
    assert task.is_queued is False
    assert task.queue_position is None
    assert attempt["status"] == AttemptStatus.FAILED.value
    assert attempt["failureMessage"] == "provider timeout"
    assert task.trace[-1]["event"] == "task.failed"
    assert task.status_history[-1]["previousStatus"] == "RENDERING"
    assert task.status_history[-1]["nextStatus"] == "FAILED"
    assert mutation.task is task
    assert mutation.attempts == [attempt]
    assert mutation.queue_event_rows[0]["eventType"] == QueueEventType.FAILED.value


def test_recompute_queue_positions_uses_queue_snapshot_order() -> None:
    coordinator = TaskExecutionCoordinator()
    task_a = _task("task_a")
    task_b = _task("task_b")
    task_c = _task("task_c")

    coordinator.task_queue_port.enqueue(task_b.id)
    coordinator.task_queue_port.enqueue(task_a.id)
    coordinator.recompute_queue_positions([task_a, task_b, task_c])

    assert task_b.is_queued is True
    assert task_b.queue_position == 1
    assert task_a.is_queued is True
    assert task_a.queue_position == 2
    assert task_c.is_queued is False
    assert task_c.queue_position is None


@pytest.mark.asyncio
async def test_recover_stale_claims_requeues_running_attempt() -> None:
    task = _task(status="RENDERING")
    coordinator = TaskExecutionCoordinator()
    coordinator.create_attempt(task, AttemptTriggerType.CREATE, {})
    coordinator.mark_active_attempt_running(task, "worker_stale")
    task.execution_context = {"workerInstanceId": "worker_stale", "clipIndex": 1}
    repository = _FakeTaskRepository(
        task=task,
        claims=[{"taskId": task.id, "workerInstanceId": "worker_stale"}],
        workers={
            "worker_stale": {
                "workerInstanceId": "worker_stale",
                "status": WorkerStatus.RUNNING.value,
                "lastHeartbeatAt": "2026-01-01T00:00:00+00:00",
            }
        },
    )

    recovered = await coordinator.recover_stale_claims(
        datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        10,
        repository,
    )

    assert recovered == 1
    assert task.status == "PENDING"
    assert task.progress == 0
    assert task.is_queued is True
    assert task.execution_context["recoveredFromWorkerInstanceId"] == "worker_stale"
    assert "workerInstanceId" not in task.execution_context
    assert _active_attempt(task)["status"] == AttemptStatus.QUEUED.value
    assert repository.saved_mutations[0].queue_event_rows[0]["eventType"] == QueueEventType.RE_ENQUEUED.value
    assert repository.saved_mutations[0].status_history_rows[0]["previousStatus"] == "RENDERING"
    assert repository.saved_mutations[0].status_history_rows[0]["nextStatus"] == "PENDING"


@pytest.mark.asyncio
async def test_recover_stale_claims_skips_worker_with_fresh_heartbeat() -> None:
    task = _task(status="RENDERING")
    coordinator = TaskExecutionCoordinator()
    coordinator.create_attempt(task, AttemptTriggerType.CREATE, {})
    coordinator.mark_active_attempt_running(task, "worker_fresh")
    repository = _FakeTaskRepository(
        task=task,
        claims=[{"taskId": task.id, "workerInstanceId": "worker_fresh"}],
        workers={
            "worker_fresh": {
                "workerInstanceId": "worker_fresh",
                "status": WorkerStatus.RUNNING.value,
                "lastHeartbeatAt": "2026-01-01T00:02:00+00:00",
            }
        },
    )

    recovered = await coordinator.recover_stale_claims(
        datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        10,
        repository,
    )

    assert recovered == 0
    assert task.status == "RENDERING"
    assert _active_attempt(task)["status"] == AttemptStatus.RUNNING.value
    assert repository.saved_mutations == []


class _FakeTaskRepository:
    def __init__(
        self,
        task: TaskRecord,
        claims: list[dict[str, Any]],
        workers: dict[str, dict[str, Any]],
    ) -> None:
        self.task = task
        self.claims = claims
        self.workers = workers
        self.saved_mutations: list[TaskPersistenceMutation] = []

    def list_stale_running_claims(self, stale_before: datetime, limit: int) -> list[dict[str, Any]]:
        return self.claims[:limit]

    def find_by_id(self, task_id: str) -> TaskRecord | None:
        return self.task if task_id == self.task.id else None

    def find_worker_instance(self, worker_instance_id: str) -> dict[str, Any] | None:
        return self.workers.get(worker_instance_id)

    def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        self.saved_mutations.append(mutation)
