from __future__ import annotations

from backend.domain.enums import AttemptStatus, AttemptTriggerType, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.services.task_attempt_lifecycle import TaskAttemptLifecycle
from backend.services.task_attempt_mutation_service import TaskAttemptMutationService
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_mutation_recorder import TaskExecutionMutationRecorder
from backend.services.task_execution_record_factory import TaskExecutionRecordFactory
from backend.services.task_queue_lifecycle import TaskQueueLifecycle
from backend.services.task_transition_service import TaskTransitionService
from backend.services.task_worker_registry import TaskWorkerRegistry


def _task() -> TaskRecord:
    return TaskRecord(
        id="task_1",
        owner_user_id=7,
        title="Task",
        status="PENDING",
        progress=25,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_attempt_lifecycle_owns_in_memory_attempt_state() -> None:
    lifecycle = TaskAttemptLifecycle()
    task = _task()

    attempt = lifecycle.create(task, AttemptTriggerType.CREATE, {"resumeFromClipIndex": 3})
    lifecycle.mark_queued(task)
    lifecycle.mark_running(task, "worker_1")
    finished, status = lifecycle.mark_finished(task, AttemptStatus.FINISHED, None)

    assert finished is attempt
    assert status is AttemptStatus.FINISHED
    assert attempt["resumeFromClipIndex"] == 3
    assert attempt["workerInstanceId"] == "worker_1"
    assert attempt["finishedAt"]


def test_record_factory_preserves_task_ownership_and_worker_context() -> None:
    factory = TaskExecutionRecordFactory()
    task = _task()
    task.active_attempt_id = "att_1"

    event = factory.queue_event(task, "CLAIMED", {"source": "test"}, "worker_1")
    request_log = factory.request_log(task, {"modelCallId": "call_1", "callKind": "video"})

    assert event["attemptId"] == "att_1"
    assert event["workerInstanceId"] == "worker_1"
    assert request_log["requestLogId"] == "reqlog_call_1"
    assert request_log["ownerUserId"] == 7
    assert request_log["requestType"] == "video"


def test_worker_registry_preserves_start_time_and_marks_terminal_heartbeat() -> None:
    registry = TaskWorkerRegistry()
    existing = registry.upsert("worker_1", "render", WorkerStatus.RUNNING.value, {"gpu": "a"})

    stopped = registry.touch(
        "worker_1",
        "render",
        WorkerStatus.STOPPED.value,
        None,
        existing,
    )

    assert stopped["startedAt"] == existing["startedAt"]
    assert stopped["metadata"] == {"gpu": "a"}
    assert stopped["stoppedAt"]


def test_execution_coordinator_composes_queue_lifecycle() -> None:
    coordinator = TaskExecutionCoordinator()

    assert isinstance(coordinator._queue_lifecycle, TaskQueueLifecycle)
    assert coordinator._queue_lifecycle._queue is coordinator.task_queue_port
    assert isinstance(coordinator._mutation_recorder, TaskExecutionMutationRecorder)
    assert isinstance(coordinator._attempt_mutations, TaskAttemptMutationService)
    assert isinstance(coordinator._transition_service, TaskTransitionService)


def test_mutation_recorder_owns_model_call_and_request_log_mutation() -> None:
    task = _task()
    recorder = TaskExecutionMutationRecorder(
        TaskExecutionRecordFactory(),
        lambda _task: "worker_1",
    )

    result = recorder.record_model_call(
        task,
        {"modelCallId": "call_1", "callKind": "image"},
    )

    assert result["model_call"] is task.model_calls[-1]
    assert result["request_log"]["requestType"] == "image"
    assert result["mutation"].model_call_rows == [result["model_call"]]
    assert result["mutation"].request_log_rows == [result["request_log"]]
