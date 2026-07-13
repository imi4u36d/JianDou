"""Atomic task-state, trace, history, attempt, and queue-event transitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.domain.enums import QueueEventType
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_attempt_mutation_service import TaskAttemptMutationService
from backend.services.task_execution_mutation_recorder import TaskExecutionMutationRecorder
from backend.services.task_state_transition import TaskStateTransition, TaskStateTransitionBuilder
from backend.shared import now_iso


class TaskTransitionService:
    def __init__(
        self,
        attempts: TaskAttemptMutationService,
        recorder: TaskExecutionMutationRecorder,
    ) -> None:
        self._attempts = attempts
        self._recorder = recorder

    def transition(
        self,
        task: TaskRecord,
        transition: TaskStateTransition | TaskStateTransitionBuilder,
        task_mutator: Callable[[TaskRecord], None] | None = None,
    ) -> dict[str, Any]:
        if task is None or transition is None:
            return {"mutation": TaskPersistenceMutation()}
        if isinstance(transition, TaskStateTransitionBuilder):
            transition = transition.build()
        previous_status = task.status
        if task_mutator is not None:
            task_mutator(task)
        self._apply_task_state(task, transition)

        trace = self._recorder.new_trace(
            transition.stage,
            transition.event,
            transition.message,
            transition.level,
            transition.payload,
        )
        history = self._recorder.new_status_history(
            task,
            previous_status,
            transition.next_status,
            transition.stage,
            transition.event,
            transition.message,
        )
        task.add_trace(trace)
        task.add_status_history(history)
        self._recorder.touch(task)
        mutation = (
            TaskPersistenceMutation()
            .set_task(task)
            .add_trace(trace)
            .add_status_history(history)
        )

        attempt = self._attempts.apply_transition(task, transition)
        if attempt is not None:
            mutation = mutation.add_attempt(attempt)
            queue_event = self._recorder.new_queue_event(
                task,
                QueueEventType.from_attempt_status(transition.attempt_status_enum),
                {
                    "status": transition.attempt_status,
                    "errorMessage": transition.attempt_error_message,
                },
            )
            mutation = mutation.add_queue_event(queue_event)
        return {
            "mutation": mutation,
            "trace": trace,
            "status_history": history,
            "attempt": attempt,
        }

    @staticmethod
    def _apply_task_state(task: TaskRecord, transition: TaskStateTransition) -> None:
        task.status = transition.next_status
        task.progress = transition.progress
        if transition.next_status == "FAILED":
            task.error_message = transition.attempt_error_message or transition.message
            task.finished_at = now_iso()
            task.is_queued = False
            task.queue_position = None
        elif transition.next_status in ("COMPLETED", "CANCELLED"):
            task.error_message = ""
            task.finished_at = now_iso()
            task.is_queued = False
            task.queue_position = None
        elif transition.next_status in ("PENDING", "ANALYZING", "PLANNING", "RENDERING"):
            task.error_message = ""
