"""Record task execution artifacts and assemble persistence mutations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.domain.enums import QueueEventType
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_execution_record_factory import TaskExecutionRecordFactory
from backend.shared import now_iso


class TaskExecutionMutationRecorder:
    """Own append-only execution records and their persistence mutations."""

    def __init__(
        self,
        record_factory: TaskExecutionRecordFactory,
        active_attempt_worker_id: Callable[[TaskRecord], str],
    ) -> None:
        self._record_factory = record_factory
        self._active_attempt_worker_id = active_attempt_worker_id

    @staticmethod
    def touch(task: TaskRecord) -> None:
        task.updated_at = now_iso()

    def new_trace(
        self,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._record_factory.trace(stage, event, message, level, payload)

    def new_status_history(
        self,
        task: TaskRecord,
        previous_status: str,
        next_status: str,
        stage: str,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._record_factory.status_history(
            task, previous_status, next_status, stage, event, reason
        )

    def new_queue_event(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._record_factory.queue_event(
            task,
            event_type,
            payload,
            self._active_attempt_worker_id(task),
        )

    def record_trace(
        self,
        task: TaskRecord,
        stage: str,
        event: str,
        message: str,
        level: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        row = self.new_trace(stage, event, message, level, payload)
        task.add_trace(row)
        self.touch(task)
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
        row = self.new_status_history(task, previous_status, next_status, stage, event, reason)
        task.add_status_history(row)
        self.touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_status_history(row),
            "status_history": row,
        }

    def record_stage_run(self, task: TaskRecord, stage_run: dict[str, Any]) -> dict[str, Any]:
        task.add_stage_run(stage_run)
        self.touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_stage_run(stage_run),
            "stage_run": stage_run,
        }

    def record_model_call(self, task: TaskRecord, model_call: dict[str, Any]) -> dict[str, Any]:
        task.add_model_call(model_call)
        self.touch(task)
        request_log = self._record_factory.request_log(task, model_call)
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

    def record_material(self, task: TaskRecord, material: dict[str, Any]) -> dict[str, Any]:
        task.add_material(material)
        self.touch(task)
        return {
            "mutation": TaskPersistenceMutation().set_task(task).add_material(material),
            "material": material,
        }

    def record_result(self, task: TaskRecord, result: dict[str, Any]) -> dict[str, Any]:
        task.add_output(result)
        self.touch(task)
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
        row = self.new_queue_event(task, event_type, payload)
        return {
            "mutation": TaskPersistenceMutation().set_task_id(task.id).add_queue_event(row),
            "queue_event": row,
        }
