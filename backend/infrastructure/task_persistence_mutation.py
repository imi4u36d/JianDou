from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.domain.task_record import TaskRecord


@dataclass
class TaskPersistenceMutation:
    """Aggregates all persistence rows produced by one task-side state transition.

    Repository adapters persist this mutation's contents in a single transaction.
    Mirrors the Java TaskPersistenceMutation builder pattern.
    """

    task_id: str = ""
    task: TaskRecord | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    status_history_rows: list[dict[str, Any]] = field(default_factory=list)
    trace_rows: list[dict[str, Any]] = field(default_factory=list)
    stage_run_rows: list[dict[str, Any]] = field(default_factory=list)
    model_call_rows: list[dict[str, Any]] = field(default_factory=list)
    request_log_rows: list[dict[str, Any]] = field(default_factory=list)
    material_rows: list[dict[str, Any]] = field(default_factory=list)
    result_rows: list[dict[str, Any]] = field(default_factory=list)
    queue_event_rows: list[dict[str, Any]] = field(default_factory=list)
    worker_instance_rows: list[dict[str, Any]] = field(default_factory=list)

    def set_task(self, value: TaskRecord | None) -> TaskPersistenceMutation:
        self.task = value
        self.task_id = "" if value is None else (value.id or "")
        return self

    def set_task_id(self, value: str) -> TaskPersistenceMutation:
        self.task_id = (value or "").strip()
        return self

    def add_attempt(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.attempts.append(value)
        return self

    def add_status_history(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.status_history_rows.append(value)
        return self

    def add_trace(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.trace_rows.append(value)
        return self

    def add_stage_run(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.stage_run_rows.append(value)
        return self

    def add_model_call(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.model_call_rows.append(value)
        return self

    def add_request_log(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.request_log_rows.append(value)
        return self

    def add_material(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.material_rows.append(value)
        return self

    def add_result(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.result_rows.append(value)
        return self

    def add_queue_event(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.queue_event_rows.append(value)
        return self

    def add_worker_instance(self, value: dict[str, Any]) -> TaskPersistenceMutation:
        if value:
            self.worker_instance_rows.append(value)
        return self
