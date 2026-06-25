from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.generation_service import GenerationProviderException
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_worker_status_stage_service import (
    TaskExecutionAbortedException,
    TaskStage,
    TaskWorkerExecutionContext,
    TaskWorkerStatusStageService,
)

pytestmark = pytest.mark.service


def _task(status: str = TaskStatus.RENDERING.value) -> TaskRecord:
    return TaskRecord(
        id="task_status_stage",
        owner_user_id=9,
        title="Status stage task",
        status=status,
        progress=10,
        active_attempt_id="attempt_1",
        attempts=[{"attemptId": "attempt_1", "status": "RUNNING"}],
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _context() -> TaskWorkerExecutionContext:
    return TaskWorkerExecutionContext("worker_1", "render", "direct")


def test_record_stage_run_creates_deterministic_completed_row() -> None:
    task = _task()
    service = TaskWorkerStatusStageService(execution_coordinator=TaskExecutionCoordinator())

    result = service.record_stage_run(
        task,
        _context(),
        200,
        TaskStage.RENDER,
        2,
        {"prompt": "input"},
        {"outputUrl": "/clip.mp4"},
    )

    mutation = result["mutation"]
    assert mutation.stage_run_rows[-1]["stageRunId"] == "stgrun_cd616029593f57dca69cd26796cca9e3"
    assert mutation.stage_run_rows[-1]["status"] == "COMPLETED"
    assert mutation.stage_run_rows[-1]["workerInstanceId"] == "worker_1"
    assert task.stage_runs[-1]["outputSummary"] == {"outputUrl": "/clip.mp4"}


def test_model_call_lifecycle_preserves_model_metadata_and_provider_errors() -> None:
    service = TaskWorkerStatusStageService()
    pending = service.create_pending_model_call(
        _task(),
        TaskStage.RENDER,
        "generation.video",
        {"model": {"providerModel": "requested-model"}},
        1,
        "video",
    )

    completed = service.complete_model_call(
        pending,
        {"id": "run_1", "updatedAt": "2026-01-01T00:00:01.000000Z"},
        {
            "modelInfo": {
                "provider": "provider",
                "providerModel": "provider-model",
                "requestedModel": "requested-model",
                "resolvedModel": "resolved-model",
                "endpointHost": "api.example.test",
            }
        },
    )

    assert pending["status"] == "pending"
    assert completed["status"] == "success"
    assert completed["success"] is True
    assert completed["requestId"] == "run_1"
    assert completed["provider"] == "provider"
    assert completed["resolvedModel"] == "resolved-model"

    failed = service.fail_model_call(
        pending,
        GenerationProviderException(
            "provider failed",
            http_status=429,
            provider_request={"prompt": "hello"},
            provider_response={"error": "rate limit"},
        ),
    )

    assert failed["status"] == "failed"
    assert failed["success"] is False
    assert failed["httpStatus"] == 429
    assert failed["responsePayload"]["providerRequest"] == {"prompt": "hello"}
    assert failed["responsePayload"]["providerResponse"] == {"error": "rate limit"}


def test_model_call_id_distinguishes_keyframe_frame_roles() -> None:
    service = TaskWorkerStatusStageService()
    task = _task()

    first = service.create_pending_model_call(
        task,
        TaskStage.PLANNING,
        "generation.image",
        {"model": {"providerModel": "image-model"}},
        1,
        "image.first",
    )
    last = service.create_pending_model_call(
        task,
        TaskStage.PLANNING,
        "generation.image",
        {"model": {"providerModel": "image-model"}},
        1,
        "image.last",
    )

    assert first["modelCallId"] != last["modelCallId"]


def test_update_status_rejects_inactive_task_when_repository_is_present() -> None:
    service = TaskWorkerStatusStageService(task_repository=_UnexpectedRepository())

    with pytest.raises(TaskExecutionAbortedException) as exc:
        service.update_status(
            _task(TaskStatus.FAILED.value),
            _context(),
            TaskStatus.RENDERING.value,
            50,
            TaskStage.RENDER,
            "task.rendering",
            "rendering",
        )

    assert exc.value.task_status == TaskStatus.FAILED.value


def test_fail_task_merges_worker_instance_mutation_and_removes_from_queue() -> None:
    queue = _RecordingQueue()
    task = _task()
    task.is_queued = True
    task.queue_position = 2
    service = TaskWorkerStatusStageService(
        task_queue_port=queue,
        execution_coordinator=TaskExecutionCoordinator(),
    )

    result = service.fail_task(task, _context(), RuntimeError("boom"))

    assert queue.removed == ["task_status_stage"]
    assert task.status == TaskStatus.FAILED.value
    assert task.is_queued is False
    assert task.queue_position is None
    mutation = result["mutation"]
    assert isinstance(mutation, TaskPersistenceMutation)
    assert mutation.worker_instance_rows[-1]["workerInstanceId"] == "worker_1"


class _RecordingQueue:
    def __init__(self) -> None:
        self.removed: list[str] = []

    def remove(self, task_id: str) -> None:
        self.removed.append(task_id)


class _UnexpectedRepository:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected repository call: {name}")
