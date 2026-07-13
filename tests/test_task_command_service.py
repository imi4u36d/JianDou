from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import AttemptStatus, AttemptTriggerType, QueueEventType, TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_command_mutations import merge_task_mutation
from backend.services.task_command_service import TaskCommandService
from backend.services.task_creation_service import TaskCreationService
from backend.services.task_execution_coordinator import TaskExecutionCoordinator

pytestmark = pytest.mark.service


def test_command_service_composes_creation_service() -> None:
    service = TaskCommandService(_RecordingTaskRepository(), TaskExecutionCoordinator())

    assert isinstance(service._creation_service, TaskCreationService)


def test_merge_task_mutation_combines_all_append_only_rows() -> None:
    task = _task_with_attempt()
    base = TaskPersistenceMutation().set_task(task)
    incoming = TaskPersistenceMutation().set_task(task)
    incoming.add_attempt({"attemptId": "attempt_1"})
    incoming.add_trace({"event": "task.created"})
    incoming.add_queue_event({"eventType": "ENQUEUED"})
    incoming.add_status_history({"nextStatus": TaskStatus.PENDING.value})
    incoming.add_request_log({"requestId": "request_1"})

    merged = merge_task_mutation(base, {"mutation": incoming})

    assert merged is base
    assert merged.task is task
    assert merged.attempts == [{"attemptId": "attempt_1"}]
    assert merged.trace_rows == [{"event": "task.created"}]
    assert merged.queue_event_rows == [{"eventType": "ENQUEUED"}]
    assert merged.status_history_rows == [{"nextStatus": TaskStatus.PENDING.value}]
    assert merged.request_log_rows == [{"requestId": "request_1"}]


def _task_with_attempt(status: str = TaskStatus.RENDERING.value) -> TaskRecord:
    task = TaskRecord(
        id="task_command",
        owner_user_id=1,
        title="Command task",
        status=status,
        progress=42,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        is_queued=True,
        queue_position=1,
    )
    coordinator = TaskExecutionCoordinator()
    coordinator.create_attempt(task, AttemptTriggerType.CREATE, {})
    coordinator.enqueue(task, "dispatch", "task.enqueued", "Task enqueued.")
    coordinator.mark_active_attempt_running(task, "worker_1")
    return task


@pytest.mark.asyncio
async def test_pause_persists_full_lifecycle_mutation() -> None:
    repository = _RecordingTaskRepository()
    service = TaskCommandService(repository, TaskExecutionCoordinator())
    task = _task_with_attempt()

    paused = await service.pause(task)

    mutation = repository.single_mutation()
    assert repository.saved_tasks == []
    assert paused.status == TaskStatus.PAUSED.value
    assert paused.is_queued is False
    assert paused.queue_position is None
    assert mutation.task is paused
    assert mutation.attempts[-1]["status"] == AttemptStatus.PAUSED.value
    assert mutation.status_history_rows[-1]["nextStatus"] == TaskStatus.PAUSED.value
    assert mutation.trace_rows[-1]["event"] == "task.paused"
    assert [row["eventType"] for row in mutation.queue_event_rows] == [
        QueueEventType.REMOVED.value,
        QueueEventType.REMOVED.value,
    ]


@pytest.mark.asyncio
async def test_terminate_persists_full_lifecycle_mutation() -> None:
    repository = _RecordingTaskRepository()
    service = TaskCommandService(repository, TaskExecutionCoordinator())
    task = _task_with_attempt()

    terminated = await service.terminate(task)

    mutation = repository.single_mutation()
    assert repository.saved_tasks == []
    assert terminated.status == TaskStatus.FAILED.value
    assert terminated.error_message == "Task manually terminated."
    assert terminated.finished_at is not None
    assert mutation.task is terminated
    assert mutation.attempts[-1]["status"] == AttemptStatus.TERMINATED.value
    assert mutation.attempts[-1]["failureMessage"] == "Task manually terminated."
    assert mutation.status_history_rows[-1]["nextStatus"] == TaskStatus.FAILED.value
    assert mutation.trace_rows[-1]["event"] == "task.terminated"
    assert [row["eventType"] for row in mutation.queue_event_rows] == [
        QueueEventType.REMOVED.value,
        QueueEventType.FAILED.value,
    ]


@pytest.mark.asyncio
async def test_retry_resets_task_timing_for_fresh_elapsed_duration() -> None:
    repository = _RecordingTaskRepository()
    service = TaskCommandService(repository, TaskExecutionCoordinator())
    task = _task_with_attempt(TaskStatus.COMPLETED.value)
    task.started_at = "2026-01-01T00:00:00+00:00"
    task.finished_at = "2026-01-01T00:05:00+00:00"

    retried = await service.retry(task)

    assert retried.status == TaskStatus.PENDING.value
    assert retried.started_at is None
    assert retried.finished_at is None
    assert repository.single_mutation().task is retried


def test_retry_payload_resumes_from_first_missing_video_clip_only() -> None:
    task = TaskRecord(
        id="task_retry",
        retry_count=2,
        storyboard_script="storyboard",
        outputs=[
            {"resultType": "image", "clipIndex": 1},
            {"resultType": "video", "clipIndex": 1},
            {"resultType": "video", "clipIndex": 3},
            {"resultType": "video_join", "clipIndex": 10003},
        ],
    )

    payload = TaskCommandService._build_retry_payload(task, AttemptTriggerType.RETRY)

    assert payload["resumeFromStage"] == "render"
    assert payload["resumeFromClipIndex"] == 2
    assert payload["completedClipCount"] == 1
    assert payload["existingClipIndices"] == [1, 3]
    assert payload["reuseStoryboard"] is True


class _RecordingTaskRepository:
    def __init__(self) -> None:
        self.saved_mutations: list[TaskPersistenceMutation] = []
        self.saved_tasks: list[TaskRecord] = []

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        self.saved_mutations.append(mutation)

    async def save(self, task: TaskRecord) -> None:
        self.saved_tasks.append(task)

    def single_mutation(self) -> TaskPersistenceMutation:
        assert len(self.saved_mutations) == 1
        return self.saved_mutations[0]

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected repository call: {name}")
