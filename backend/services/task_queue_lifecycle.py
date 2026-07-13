"""Queue membership lifecycle and persistence mutations for tasks."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import QueueEventType
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.services.task_attempt_lifecycle import TaskAttemptLifecycle
from backend.services.task_execution_record_factory import TaskExecutionRecordFactory
from backend.shared import now_iso


class TaskQueueLifecycle:
    def __init__(
        self,
        queue: TaskQueuePort,
        attempts: TaskAttemptLifecycle,
        records: TaskExecutionRecordFactory,
    ) -> None:
        self._queue = queue
        self._attempts = attempts
        self._records = records

    def enqueue(
        self,
        task: TaskRecord,
        stage: str,
        event: str,
        message: str,
    ) -> dict[str, Any]:
        previous_status = task.status
        self._queue.remove(task.id)
        task.status = "PENDING"
        task.error_message = ""
        task.finished_at = None
        task.is_queued = True
        attempt = self._attempts.mark_queued(task)
        self._queue.enqueue(task.id)
        task.updated_at = now_iso()

        trace = self._records.trace(stage, event, message, "INFO", {"queue_mode": True})
        status_history = self._records.status_history(
            task, previous_status, "PENDING", stage, event, message
        )
        queue_event = self._records.queue_event(
            task,
            QueueEventType.ENQUEUED,
            {"stage": stage, "event": event, "message": message},
            self._attempts.active_worker_id(task),
        )
        task.add_trace(trace)
        task.add_status_history(status_history)

        mutation = (
            TaskPersistenceMutation()
            .set_task(task)
            .add_trace(trace)
            .add_status_history(status_history)
            .add_queue_event(queue_event)
        )
        if attempt is not None:
            mutation = mutation.add_attempt(attempt)
        return {
            "mutation": mutation,
            "trace": trace,
            "status_history": status_history,
            "queue_event": queue_event,
            "attempt": attempt,
        }

    def dequeue(self, task: TaskRecord) -> dict[str, Any]:
        was_queued = task.is_queued or task.queue_position is not None
        self._queue.remove(task.id)
        task.is_queued = False
        task.queue_position = None
        task.updated_at = now_iso()
        mutation = TaskPersistenceMutation().set_task(task)
        queue_event = None
        if was_queued:
            queue_event = self._records.queue_event(
                task,
                QueueEventType.REMOVED,
                {"queue_mode": True},
                self._attempts.active_worker_id(task),
            )
            mutation = mutation.add_queue_event(queue_event)
        return {"mutation": mutation, "queue_event": queue_event}

    def recompute_positions(self, tasks: list[TaskRecord]) -> None:
        positions = {task_id: index + 1 for index, task_id in enumerate(self.snapshot())}
        for task in tasks:
            task.queue_position = positions.get(task.id)
            task.is_queued = task.queue_position is not None

    def snapshot(self) -> list[str]:
        return list(self._queue.snapshot())
