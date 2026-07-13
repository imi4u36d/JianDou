"""Factories for task execution audit and queue records."""

from __future__ import annotations

import uuid
from typing import Any

from backend.domain.enums import QueueEventType
from backend.domain.task_record import TaskRecord
from backend.shared import now_iso, string_value


class TaskExecutionRecordFactory:
    """Build persistence-ready records without mutating task state."""

    def trace(
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

    def status_history(
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

    def queue_event(
        self,
        task: TaskRecord,
        event_type: str | QueueEventType,
        payload: dict[str, Any] | None,
        worker_instance_id: str,
    ) -> dict[str, Any]:
        event_type_str = event_type.value if isinstance(event_type, QueueEventType) else event_type
        return {
            "taskQueueEventId": "queueevt_" + uuid.uuid4().hex,
            "taskId": task.id,
            "attemptId": task.active_attempt_id if task.active_attempt_id else "",
            "queueName": "default",
            "eventType": event_type_str,
            "workerInstanceId": worker_instance_id,
            "queuePositionHint": task.queue_position if task.queue_position is not None else 0,
            "payload": payload if payload is not None else {},
            "eventTime": now_iso(),
        }

    def request_log(
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
                "reqlog_" + uuid.uuid4().hex if not model_call_id else "reqlog_" + model_call_id
            )
        row["requestLogId"] = request_log_id
        row["ownerUserId"] = task.owner_user_id if task else None
        row["ownerRefId"] = task.id if task else ""
        row["taskId"] = task.id if task else ""
        row["workflowId"] = ""
        row["requestType"] = (model_call or {}).get("callKind", "")
        return row
