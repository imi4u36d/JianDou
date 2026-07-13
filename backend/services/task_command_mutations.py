"""Composition helpers for task command persistence mutations."""

from __future__ import annotations

from typing import Any

from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation


def merge_task_mutation(
    base: TaskPersistenceMutation,
    result: dict[str, Any] | None,
) -> TaskPersistenceMutation:
    if not result:
        return base
    mutation = result.get("mutation")
    if not isinstance(mutation, TaskPersistenceMutation):
        return base
    if mutation.task is not None:
        base.task = mutation.task
    if mutation.task_id:
        base.task_id = mutation.task_id
    base.attempts.extend(mutation.attempts)
    base.status_history_rows.extend(mutation.status_history_rows)
    base.trace_rows.extend(mutation.trace_rows)
    base.stage_run_rows.extend(mutation.stage_run_rows)
    base.model_call_rows.extend(mutation.model_call_rows)
    base.request_log_rows.extend(mutation.request_log_rows)
    base.material_rows.extend(mutation.material_rows)
    base.result_rows.extend(mutation.result_rows)
    base.queue_event_rows.extend(mutation.queue_event_rows)
    base.worker_instance_rows.extend(mutation.worker_instance_rows)
    return base
