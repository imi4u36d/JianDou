"""Attempt lifecycle mutations and their queue-event persistence rows."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptStatus, AttemptTriggerType, QueueEventType
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_attempt_lifecycle import TaskAttemptLifecycle
from backend.services.task_execution_mutation_recorder import TaskExecutionMutationRecorder
from backend.services.task_state_transition import TaskStateTransition


class TaskAttemptMutationService:
    def __init__(
        self,
        lifecycle: TaskAttemptLifecycle,
        recorder: TaskExecutionMutationRecorder,
    ) -> None:
        self._lifecycle = lifecycle
        self._recorder = recorder

    def create(
        self,
        task: TaskRecord,
        trigger_type: str | AttemptTriggerType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        row = self._lifecycle.create(task, trigger_type, payload)
        self._recorder.touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_attempt(row),
            "attempt": row,
        }

    def mark_queued(self, task: TaskRecord) -> dict[str, Any] | None:
        attempt = self._lifecycle.mark_queued(task)
        if attempt is None:
            return None
        return {
            "mutation": TaskPersistenceMutation().set_task_id(task.id).add_attempt(attempt),
            "attempt": attempt,
        }

    def mark_running(
        self,
        task: TaskRecord,
        worker_instance_id: str,
    ) -> dict[str, Any] | None:
        attempt = self._lifecycle.mark_running(task, worker_instance_id)
        if attempt is None:
            return None
        queue_event = self._recorder.new_queue_event(
            task,
            QueueEventType.CLAIMED,
            {"workerInstanceId": worker_instance_id or ""},
        )
        mutation = (
            TaskPersistenceMutation()
            .set_task_id(task.id)
            .add_attempt(attempt)
            .add_queue_event(queue_event)
        )
        return {"mutation": mutation, "attempt": attempt, "queue_event": queue_event}

    def mark_finished(
        self,
        task: TaskRecord,
        status: AttemptStatus | str,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        attempt, attempt_status = self._lifecycle.mark_finished(task, status, error_message)
        if attempt is None:
            return None
        queue_event = self._recorder.new_queue_event(
            task,
            QueueEventType.from_attempt_status(attempt_status),
            {"status": attempt_status.value, "errorMessage": error_message or ""},
        )
        mutation = (
            TaskPersistenceMutation()
            .set_task_id(task.id)
            .add_attempt(attempt)
            .add_queue_event(queue_event)
        )
        return {"mutation": mutation, "attempt": attempt, "queue_event": queue_event}

    def apply_transition(
        self,
        task: TaskRecord,
        transition: TaskStateTransition,
    ) -> dict[str, Any] | None:
        return self._lifecycle.apply_transition(task, transition)
