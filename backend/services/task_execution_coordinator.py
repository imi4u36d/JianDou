"""Task execution coordinator.

Translates the Java TaskExecutionCoordinator. Handles enqueue/dequeue,
attempt lifecycle, state transitions, trace/status-history recording, and
worker instance management.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from backend.domain.enums import (
    AttemptStatus,
    AttemptTriggerType,
    QueueEventType,
)
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import InMemoryTaskQueue, TaskQueuePort
from backend.services.task_attempt_lifecycle import TaskAttemptLifecycle
from backend.services.task_attempt_mutation_service import TaskAttemptMutationService
from backend.services.task_execution_mutation_recorder import TaskExecutionMutationRecorder
from backend.services.task_execution_record_factory import TaskExecutionRecordFactory
from backend.services.task_queue_lifecycle import TaskQueueLifecycle
from backend.services.task_stale_claim_recovery import TaskStaleClaimRecovery
from backend.services.task_state_transition import TaskStateTransition, TaskStateTransitionBuilder
from backend.services.task_transition_service import TaskTransitionService
from backend.services.task_worker_registry import TaskWorkerRegistry


class TaskExecutionCoordinator:
    """Coordinates task execution lifecycle: queue, attempt, state transition."""

    def __init__(
        self,
        task_queue_port: TaskQueuePort | None = None,
    ) -> None:
        self._task_queue_port: TaskQueuePort = task_queue_port or InMemoryTaskQueue()
        self._attempt_lifecycle = TaskAttemptLifecycle()
        self._record_factory = TaskExecutionRecordFactory()
        self._mutation_recorder = TaskExecutionMutationRecorder(
            self._record_factory,
            self._attempt_lifecycle.active_worker_id,
        )
        self._attempt_mutations = TaskAttemptMutationService(
            self._attempt_lifecycle,
            self._mutation_recorder,
        )
        self._transition_service = TaskTransitionService(
            self._attempt_mutations,
            self._mutation_recorder,
        )
        self._queue_lifecycle = TaskQueueLifecycle(
            self._task_queue_port,
            self._attempt_lifecycle,
            self._record_factory,
        )
        self._worker_registry = TaskWorkerRegistry()
        self._stale_claim_recovery = TaskStaleClaimRecovery(self)

    @property
    def task_queue_port(self) -> TaskQueuePort:
        return self._task_queue_port

    # ------------------------------------------------------------------
    # Enqueue / Dequeue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        task: TaskRecord,
        stage: str,
        event: str,
        message: str,
    ) -> dict[str, Any]:
        return self._queue_lifecycle.enqueue(task, stage, event, message)

    def dequeue(self, task: TaskRecord) -> dict[str, Any]:
        return self._queue_lifecycle.dequeue(task)

    def recompute_queue_positions(self, tasks: list[TaskRecord]) -> None:
        self._queue_lifecycle.recompute_positions(tasks)

    def queue_snapshot(self) -> list[str]:
        return self._queue_lifecycle.snapshot()

    # ------------------------------------------------------------------
    # Attempt lifecycle
    # ------------------------------------------------------------------

    def create_attempt(
        self,
        task: TaskRecord,
        trigger_type: str | AttemptTriggerType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._attempt_mutations.create(task, trigger_type, payload)

    def mark_active_attempt_queued(self, task: TaskRecord) -> dict[str, Any] | None:
        return self._attempt_mutations.mark_queued(task)

    def mark_active_attempt_running(
        self,
        task: TaskRecord,
        worker_instance_id: str,
    ) -> dict[str, Any] | None:
        return self._attempt_mutations.mark_running(task, worker_instance_id)

    def mark_active_attempt_finished(
        self,
        task: TaskRecord,
        status: AttemptStatus | str,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        return self._attempt_mutations.mark_finished(task, status, error_message)

    # ------------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------------

    def transition_task(
        self,
        task: TaskRecord,
        transition: TaskStateTransition | TaskStateTransitionBuilder,
        task_mutator: Callable[[TaskRecord], None] | None = None,
    ) -> dict[str, Any]:
        return self._transition_service.transition(task, transition, task_mutator)

    def record_trace(
        self,
        task: TaskRecord,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_trace(task, stage, event, message, level, payload)

    def record_status_history(
        self,
        task: TaskRecord,
        previous_status: str,
        next_status: str,
        stage: str,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_status_history(
            task, previous_status, next_status, stage, event, reason
        )

    def record_stage_run(
        self,
        task: TaskRecord,
        stage_run: dict[str, Any],
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_stage_run(task, stage_run)

    def record_model_call(
        self,
        task: TaskRecord,
        model_call: dict[str, Any],
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_model_call(task, model_call)

    def record_material(
        self,
        task: TaskRecord,
        material: dict[str, Any],
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_material(task, material)

    def record_result(
        self,
        task: TaskRecord,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_result(task, result)

    def record_queue_event(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._mutation_recorder.record_queue_event(task, event_type, payload)

    # ------------------------------------------------------------------
    # Worker instance management
    # ------------------------------------------------------------------

    def upsert_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        row = self._worker_registry.upsert(worker_instance_id, worker_type, status, metadata)
        return {
            "mutation": TaskPersistenceMutation().add_worker_instance(row),
            "worker_instance": row,
        }

    def touch_worker_instance(
        self,
        worker_instance_id: str,
        worker_type: str,
        status: str,
        metadata: dict[str, Any] | None,
        existing_instance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = self._worker_registry.touch(
            worker_instance_id,
            worker_type,
            status,
            metadata,
            existing_instance,
        )
        return {
            "mutation": TaskPersistenceMutation().add_worker_instance(row),
            "worker_instance": row,
        }

    async def recover_stale_claims(
        self,
        stale_before: datetime,
        limit: int,
        task_repository: Any,  # TaskRepository protocol
    ) -> int:
        return await self._stale_claim_recovery.recover(stale_before, limit, task_repository)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _active_attempt(self, task: TaskRecord) -> dict[str, Any] | None:
        return self._attempt_lifecycle.active(task)

    def _active_attempt_worker_id(self, task: TaskRecord) -> str:
        return self._attempt_lifecycle.active_worker_id(task)

    def _mark_active_attempt_queued_in_memory(
        self,
        task: TaskRecord,
    ) -> dict[str, Any] | None:
        return self._attempt_lifecycle.mark_queued(task)

    def _touch(self, task: TaskRecord) -> None:
        self._mutation_recorder.touch(task)

    def _new_trace_row(
        self,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._mutation_recorder.new_trace(stage, event, message, level, payload)

    def _new_status_history_row(
        self,
        task: TaskRecord,
        previous_status: str,
        next_status: str,
        stage: str,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._mutation_recorder.new_status_history(
            task, previous_status, next_status, stage, event, reason
        )

    def _new_queue_event_row(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._mutation_recorder.new_queue_event(task, event_type, payload)

    def _apply_attempt_transition(
        self,
        task: TaskRecord,
        transition: TaskStateTransition,
    ) -> dict[str, Any] | None:
        return self._attempt_mutations.apply_transition(task, transition)
