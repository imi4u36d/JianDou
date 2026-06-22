"""Task execution coordinator.

Translates the Java TaskExecutionCoordinator. Handles enqueue/dequeue,
attempt lifecycle, state transitions, trace/status-history recording, and
worker instance management.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from backend.domain.enums import (
    AttemptStatus,
    AttemptTriggerType,
    QueueEventType,
    WorkerStatus,
)
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import InMemoryTaskQueue, TaskQueuePort
from backend.shared import now_iso, safe_int, string_value


class TaskExecutionCoordinator:
    """Coordinates task execution lifecycle: queue, attempt, state transition."""

    def __init__(
        self,
        task_queue_port: TaskQueuePort | None = None,
    ) -> None:
        self._task_queue_port: TaskQueuePort = task_queue_port or InMemoryTaskQueue()

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
        """Set task to PENDING, mark active attempt as QUEUED, persist."""
        previous_status = task.status
        self._task_queue_port.remove(task.id)
        task.status = "PENDING"
        task.error_message = ""
        task.finished_at = None
        task.is_queued = True
        attempt = self._mark_active_attempt_queued_in_memory(task)
        self._task_queue_port.enqueue(task.id)
        self._touch(task)

        trace = self._new_trace_row(stage, event, message, "INFO", {"queue_mode": True})
        status_history = self._new_status_history_row(
            task, previous_status, "PENDING", stage, event, message,
        )
        queue_event = self._new_queue_event_row(
            task, QueueEventType.ENQUEUED, {"stage": stage, "event": event, "message": message},
        )
        task.add_trace(trace)
        task.add_status_history(status_history)

        mutation = (
            TaskPersistenceMutation()
            .set_task(task)
        )
        mutation = mutation.add_trace(trace)
        mutation = mutation.add_status_history(status_history)
        mutation = mutation.add_queue_event(queue_event)
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
        """Remove task from queue, clear queued flag."""
        was_queued = task.is_queued or task.queue_position is not None
        self._task_queue_port.remove(task.id)
        task.is_queued = False
        task.queue_position = None
        self._touch(task)
        mutation = TaskPersistenceMutation().set_task(task)
        if was_queued:
            queue_event = self._new_queue_event_row(
                task, QueueEventType.REMOVED, {"queue_mode": True},
            )
            mutation = mutation.add_queue_event(queue_event)
        else:
            queue_event = None
        return {"mutation": mutation, "queue_event": queue_event}

    def recompute_queue_positions(self, tasks: list[TaskRecord]) -> None:
        """Recalculate queue positions for all tasks."""
        positions: dict[str, int] = {}
        snapshot = self.queue_snapshot()
        for index, tid in enumerate(snapshot):
            positions[tid] = index + 1
        for item in tasks:
            position = positions.get(item.id)
            item.queue_position = position
            item.is_queued = position is not None

    def queue_snapshot(self) -> list[str]:
        """Return ordered list of queued task IDs."""
        return list(self._task_queue_port.snapshot())

    # ------------------------------------------------------------------
    # Attempt lifecycle
    # ------------------------------------------------------------------

    def create_attempt(
        self,
        task: TaskRecord,
        trigger_type: str | AttemptTriggerType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Create a new attempt record, prepend it to task.attempts."""
        if isinstance(trigger_type, AttemptTriggerType):
            trigger_str = trigger_type.value
        else:
            trigger_str = AttemptTriggerType._missing_(trigger_type)
            if trigger_str is None:
                trigger_str = string_value(trigger_type).lower()

        task.current_attempt_no += 1
        attempt_id = "att_" + uuid.uuid4().hex
        safe_payload = payload if payload is not None else {}

        row: dict[str, Any] = {
            "attemptId": attempt_id,
            "taskId": task.id,
            "attemptNo": task.current_attempt_no,
            "triggerType": trigger_str,
            "status": AttemptStatus.CREATED.value,
            "queueName": "default",
            "workerInstanceId": "",
            "queueEnteredAt": None,
            "queueLeftAt": None,
            "claimedAt": None,
            "startedAt": None,
            "finishedAt": None,
            "resumeFromStage": string_value(safe_payload.get("resumeFromStage")),
            "resumeFromClipIndex": safe_int(safe_payload.get("resumeFromClipIndex"), 0),
            "failureCode": "",
            "failureMessage": "",
            "payload": safe_payload,
        }
        task.active_attempt_id = attempt_id
        task.prepend_attempt(row)
        self._touch(task)

        mutation = TaskPersistenceMutation().set_task(task).add_attempt(row)
        return {
            "mutation": mutation,
            "attempt": row,
        }

    def mark_active_attempt_queued(self, task: TaskRecord) -> dict[str, Any] | None:
        attempt = self._mark_active_attempt_queued_in_memory(task)
        if attempt is None:
            return None
        return {
            "mutation": TaskPersistenceMutation().set_task_id(task.id).add_attempt(attempt),
            "attempt": attempt,
        }

    def mark_active_attempt_running(
        self,
        task: TaskRecord,
        worker_instance_id: str,
    ) -> dict[str, Any] | None:
        attempt = self._active_attempt(task)
        if attempt is None:
            return None
        now = now_iso()
        attempt["status"] = AttemptStatus.RUNNING.value
        attempt["workerInstanceId"] = worker_instance_id if worker_instance_id else ""
        attempt["claimedAt"] = now
        attempt["queueLeftAt"] = now
        attempt["startedAt"] = now
        queue_event = self._new_queue_event_row(
            task,
            QueueEventType.CLAIMED,
            {"workerInstanceId": worker_instance_id if worker_instance_id else ""},
        )
        mutation = (
            TaskPersistenceMutation()
            .set_task_id(task.id)
            .add_attempt(attempt)
            .add_queue_event(queue_event)
        )
        return {"mutation": mutation, "attempt": attempt, "queue_event": queue_event}

    def mark_active_attempt_finished(
        self,
        task: TaskRecord,
        status: AttemptStatus | str,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        if isinstance(status, str):
            attempt_status = AttemptStatus._missing_(status)
            if attempt_status is None:
                attempt_status = AttemptStatus.FINISHED
        else:
            attempt_status = status
        attempt = self._active_attempt(task)
        if attempt is None:
            return None
        now = now_iso()
        attempt["status"] = attempt_status.value
        attempt["finishedAt"] = now
        if error_message and error_message.strip():
            attempt["failureMessage"] = error_message
        queue_event = self._new_queue_event_row(
            task,
            QueueEventType.from_attempt_status(attempt_status),
            {
                "status": attempt_status.value,
                "errorMessage": error_message or "",
            },
        )
        mutation = (
            TaskPersistenceMutation()
            .set_task_id(task.id)
            .add_attempt(attempt)
            .add_queue_event(queue_event)
        )
        return {"mutation": mutation, "attempt": attempt, "queue_event": queue_event}

    # ------------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------------

    def transition_task(
        self,
        task: TaskRecord,
        transition: TaskStateTransition | TaskStateTransitionBuilder,
        task_mutator: Callable[[TaskRecord], None] | None = None,
    ) -> dict[str, Any]:
        """Atomically transition task state, recording trace + status history."""
        if task is None or transition is None:
            return {"mutation": TaskPersistenceMutation()}
        if isinstance(transition, TaskStateTransitionBuilder):
            transition = transition.build()

        previous_status = task.status

        if task_mutator is not None:
            task_mutator(task)

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

        trace = self._new_trace_row(
            transition.stage,
            transition.event,
            transition.message,
            transition.level,
            transition.payload,
        )
        status_history = self._new_status_history_row(
            task,
            previous_status,
            transition.next_status,
            transition.stage,
            transition.event,
            transition.message,
        )
        task.add_trace(trace)
        task.add_status_history(status_history)
        self._touch(task)

        mutation = (
            TaskPersistenceMutation()
            .set_task(task)
            .add_trace(trace)
            .add_status_history(status_history)
        )

        attempt = self._apply_attempt_transition(task, transition)
        if attempt is not None:
            mutation = mutation.add_attempt(attempt)
            queue_event = self._new_queue_event_row(
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
            "status_history": status_history,
            "attempt": attempt,
        }

    def record_trace(
        self,
        task: TaskRecord,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        row = self._new_trace_row(stage, event, message, level, payload)
        task.add_trace(row)
        self._touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_trace(row),
            "trace": row,
        }

    def record_status_history(
        self,
        task: TaskRecord,
        previous_status: str,
        next_status: str,
        stage: str,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        row = self._new_status_history_row(task, previous_status, next_status, stage, event, reason)
        task.add_status_history(row)
        self._touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_status_history(row),
            "status_history": row,
        }

    def record_stage_run(
        self,
        task: TaskRecord,
        stage_run: dict[str, Any],
    ) -> dict[str, Any]:
        task.add_stage_run(stage_run)
        self._touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_stage_run(stage_run),
            "stage_run": stage_run,
        }

    def record_model_call(
        self,
        task: TaskRecord,
        model_call: dict[str, Any],
    ) -> dict[str, Any]:
        task.add_model_call(model_call)
        self._touch(task)
        request_log = self._to_request_log(task, model_call)
        return {
            "mutation": (
                TaskPersistenceMutation()
                .set_task(task)
                .add_model_call(model_call)
                .add_request_log(request_log)
            ),
            "model_call": model_call,
            "request_log": request_log,
        }

    def record_material(
        self,
        task: TaskRecord,
        material: dict[str, Any],
    ) -> dict[str, Any]:
        task.add_material(material)
        self._touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_material(material),
            "material": material,
        }

    def record_result(
        self,
        task: TaskRecord,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        task.add_output(result)
        self._touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_result(result),
            "result": result,
        }

    def record_queue_event(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if isinstance(event_type, QueueEventType):
            row = self._new_queue_event_row(task, event_type, payload)
        else:
            row = self._new_queue_event_row(task, event_type, payload)
        return {
            "mutation": TaskPersistenceMutation().set_task_id(task.id).add_queue_event(row),
            "queue_event": row,
        }

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
        now = now_iso()
        row: dict[str, Any] = {
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "queueName": "default",
            "hostName": "",
            "processId": 0,
            "status": status,
            "startedAt": now,
            "lastHeartbeatAt": now,
            "stoppedAt": "",
            "metadata": metadata if metadata is not None else {},
        }
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
        now = now_iso()
        started_at = (
            string_value(existing_instance.get("startedAt", now))
            if existing_instance
            else now
        )
        row: dict[str, Any] = {
            "workerInstanceId": worker_instance_id,
            "workerType": worker_type,
            "queueName": string_value(existing_instance.get("queueName", "default")) if existing_instance else "default",
            "hostName": string_value(existing_instance.get("hostName", "")) if existing_instance else "",
            "processId": existing_instance.get("processId", 0) if existing_instance else 0,
            "status": status,
            "startedAt": started_at,
            "lastHeartbeatAt": now,
            "stoppedAt": (
                now
                if status in (WorkerStatus.STOPPED.value, WorkerStatus.FAILED.value)
                else string_value(existing_instance.get("stoppedAt", "")) if existing_instance else ""
            ),
            "metadata": (
                metadata
                if metadata is not None
                else (existing_instance.get("metadata", {}) if existing_instance else {})
            ),
        }
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
        """Recover tasks claimed by stale workers. Returns count recovered."""
        recovered = 0

        # Mark stale workers (simplified - in real impl, list stale workers and
        # mark them; here we rely on repository methods)
        # Worker marking would happen in a real implementation via
        # task_repository.list_stale_worker_instance_ids and then transition

        # Stale running claims recovery
        from backend.domain.task_record import _string_value as _sv

        stale_str = stale_before.isoformat() if hasattr(stale_before, "isoformat") else str(stale_before)
        stale_claims = task_repository.list_stale_running_claims(stale_before, limit)
        if hasattr(stale_claims, "__await__"):
            stale_claims = await stale_claims
        for claim in stale_claims:
            tid = _sv(claim.get("taskId", ""))
            if not tid:
                continue
            task = task_repository.find_by_id(tid)
            if hasattr(task, "__await__"):
                task = await task
            if task is None:
                continue
            attempt = self._active_attempt(task)
            if attempt is None or _sv(attempt.get("status", "")) != "RUNNING":
                continue

            stale_worker_id = _sv(claim.get("workerInstanceId", ""))
            worker_instance = None
            if stale_worker_id and hasattr(task_repository, "find_worker_instance"):
                worker_instance = task_repository.find_worker_instance(stale_worker_id)
                if hasattr(worker_instance, "__await__"):
                    worker_instance = await worker_instance
            if worker_instance is not None:
                last_heartbeat = _sv(worker_instance.get("lastHeartbeatAt", ""))
                worker_status = _sv(worker_instance.get("status", ""))
                if worker_status == WorkerStatus.RUNNING.value and last_heartbeat >= stale_str:
                    continue
            previous_status = task.status
            task.status = "PENDING"
            task.progress = 0
            task.error_message = ""
            task.finished_at = None
            task.is_queued = True
            task.queue_position = None
            if task.execution_context:
                task.mutable_execution_context()["recoveredFromWorkerInstanceId"] = stale_worker_id
                task.mutable_execution_context().pop("workerInstanceId", None)

            queued_attempt = self._mark_active_attempt_queued_in_memory(task)
            queue_event = self._new_queue_event_row(
                task,
                "re_enqueued",
                {
                    "reason": "stale_claim_recovered",
                    "staleWorkerInstanceId": stale_worker_id,
                },
            )
            trace = self._new_trace_row(
                "dispatch",
                "task.recovered_from_stale_claim",
                "Detected stale worker; task re-enqueued.",
                "WARN",
                {"staleWorkerInstanceId": stale_worker_id},
            )
            status_history = self._new_status_history_row(
                task,
                previous_status,
                "PENDING",
                "dispatch",
                "task.recovered_from_stale_claim",
                "Detected stale worker; task re-enqueued.",
            )
            task.add_trace(trace)
            task.add_status_history(status_history)
            self._touch(task)

            mutation = (
                TaskPersistenceMutation()
                .set_task(task)
                .add_queue_event(queue_event)
                .add_trace(trace)
                .add_status_history(status_history)
            )
            if queued_attempt is not None:
                mutation = mutation.add_attempt(queued_attempt)
            save_result = task_repository.save_mutation(mutation)
            if hasattr(save_result, "__await__"):
                await save_result
            recovered += 1

        return recovered

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _touch(self, task: TaskRecord) -> None:
        task.updated_at = now_iso()

    def _active_attempt(self, task: TaskRecord) -> dict[str, Any] | None:
        if not task.active_attempt_id:
            return None
        for row in task.attempts:
            if task.active_attempt_id == string_value(row.get("attemptId", "")):
                return row
        return None

    def _active_attempt_worker_id(self, task: TaskRecord) -> str:
        attempt = self._active_attempt(task)
        if attempt is None:
            return ""
        return string_value(attempt.get("workerInstanceId"))

    def _mark_active_attempt_queued_in_memory(
        self,
        task: TaskRecord,
    ) -> dict[str, Any] | None:
        attempt = self._active_attempt(task)
        if attempt is None:
            return None
        now = now_iso()
        attempt["status"] = AttemptStatus.QUEUED.value
        attempt["queueEnteredAt"] = now
        attempt["queueLeftAt"] = None
        attempt["claimedAt"] = None
        attempt["startedAt"] = None
        attempt["workerInstanceId"] = ""
        attempt["finishedAt"] = None
        attempt["failureMessage"] = ""
        return attempt

    def _apply_attempt_transition(
        self,
        task: TaskRecord,
        transition: TaskStateTransition,
    ) -> dict[str, Any] | None:
        if task is None or transition is None or not transition.updates_attempt:
            return None
        attempt = self._active_attempt(task)
        if attempt is None:
            return None
        now = now_iso()
        status = transition.attempt_status_enum
        attempt["status"] = transition.attempt_status
        if status == AttemptStatus.QUEUED:
            attempt["queueEnteredAt"] = now
            attempt["queueLeftAt"] = None
            attempt["claimedAt"] = None
            attempt["startedAt"] = None
            attempt["workerInstanceId"] = ""
            attempt["finishedAt"] = None
            attempt["failureMessage"] = ""
            return attempt
        if status == AttemptStatus.RUNNING:
            attempt["queueLeftAt"] = now
            attempt["claimedAt"] = now
            attempt["startedAt"] = now
            attempt["finishedAt"] = None
            attempt["failureMessage"] = ""
            return attempt
        attempt["finishedAt"] = now
        attempt["failureMessage"] = transition.attempt_error_message
        return attempt

    def _new_trace_row(
        self,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "traceId": "trace_" + uuid.uuid4().hex,
            "timestamp": now_iso(),
            "level": level,
            "stage": stage,
            "event": event,
            "message": message,
            "payload": payload if payload is not None else {},
        }

    def _new_status_history_row(
        self,
        task: TaskRecord,
        previous_status: str,
        next_status: str,
        stage: str,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "statusHistoryId": "sthis_" + uuid.uuid4().hex,
            "taskId": task.id,
            "previousStatus": previous_status,
            "nextStatus": next_status,
            "progress": task.progress,
            "stage": stage,
            "event": event,
            "reason": reason,
            "operator": "system",
            "changedAt": now_iso(),
            "payload": {},
        }

    def _new_queue_event_row(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        event_type_str = event_type.value if isinstance(event_type, QueueEventType) else event_type
        return {
            "taskQueueEventId": "queueevt_" + uuid.uuid4().hex,
            "taskId": task.id,
            "attemptId": task.active_attempt_id if task.active_attempt_id else "",
            "queueName": "default",
            "eventType": event_type_str,
            "workerInstanceId": self._active_attempt_worker_id(task),
            "queuePositionHint": task.queue_position if task.queue_position is not None else 0,
            "payload": payload if payload is not None else {},
            "eventTime": now_iso(),
        }

    def _to_request_log(
        self,
        task: TaskRecord,
        model_call: dict[str, Any] | None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {}
        if model_call:
            row.update(model_call)
        request_log_id = string_value(row.get("requestLogId"))
        if not request_log_id:
            model_call_id = string_value(row.get("modelCallId"))
            request_log_id = (
                "reqlog_" + uuid.uuid4().hex
                if not model_call_id
                else "reqlog_" + model_call_id
            )
        row["requestLogId"] = request_log_id
        row["ownerUserId"] = task.owner_user_id if task else None
        row["ownerRefId"] = task.id if task else ""
        row["taskId"] = task.id if task else ""
        row["workflowId"] = ""
        row["requestType"] = (model_call or {}).get("callKind", "")
        return row


class TaskStateTransition:
    """Value object for a task state transition.

    Mirrors Java TaskStateTransition with builder pattern.
    """

    def __init__(
        self,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
        attempt_status: str = "",
        attempt_error_message: str = "",
        updates_attempt: bool = False,
    ) -> None:
        self._next_status = next_status
        self._progress = progress
        self._stage = stage
        self._event = event
        self._message = message
        self._level = level
        self._payload = payload if payload is not None else {}
        self._attempt_status = attempt_status
        self._attempt_error_message = attempt_error_message
        self._updates_attempt = updates_attempt

    @property
    def next_status(self) -> str:
        return self._next_status

    @property
    def progress(self) -> int:
        return self._progress

    @property
    def stage(self) -> str:
        return self._stage

    @property
    def event(self) -> str:
        return self._event

    @property
    def message(self) -> str:
        return self._message

    @property
    def level(self) -> str:
        return self._level

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    @property
    def attempt_status(self) -> str:
        return self._attempt_status

    @property
    def attempt_status_enum(self) -> AttemptStatus:
        result = AttemptStatus._missing_(self._attempt_status)
        return result if result is not None else AttemptStatus.CREATED

    @property
    def attempt_error_message(self) -> str:
        return self._attempt_error_message

    @property
    def updates_attempt(self) -> bool:
        return self._updates_attempt

    @staticmethod
    def info(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "INFO", payload)

    @staticmethod
    def warn(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "WARN", payload)

    @staticmethod
    def error(
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransitionBuilder:
        return TaskStateTransitionBuilder(next_status, progress, stage, event, message, "ERROR", payload)


class TaskStateTransitionBuilder:
    """Builder for TaskStateTransition with attempt chaining."""

    def __init__(
        self,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> None:
        self._next_status = next_status
        self._progress = progress
        self._stage = stage
        self._event = event
        self._message = message
        self._level = level
        self._payload = payload if payload is not None else {}

    def with_attempt(
        self,
        attempt_status: AttemptStatus | str,
        error_message: str = "",
    ) -> TaskStateTransition:
        if isinstance(attempt_status, AttemptStatus):
            status_str = attempt_status.value
        else:
            status_str = attempt_status
        return TaskStateTransition(
            next_status=self._next_status,
            progress=self._progress,
            stage=self._stage,
            event=self._event,
            message=self._message,
            level=self._level,
            payload=self._payload,
            attempt_status=status_str,
            attempt_error_message=error_message or "",
            updates_attempt=True,
        )

    def build(self) -> TaskStateTransition:
        return TaskStateTransition(
            next_status=self._next_status,
            progress=self._progress,
            stage=self._stage,
            event=self._event,
            message=self._message,
            level=self._level,
            payload=self._payload,
        )
