"""In-memory lifecycle operations for task execution attempts."""

from __future__ import annotations

import uuid
from typing import Any

from backend.domain.enums import AttemptStatus, AttemptTriggerType
from backend.domain.task_record import TaskRecord
from backend.services.task_state_transition import TaskStateTransition
from backend.shared import now_iso, safe_int, string_value


class TaskAttemptLifecycle:
    """Create and transition attempt records without persistence concerns."""

    def create(
        self,
        task: TaskRecord,
        trigger_type: str | AttemptTriggerType,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
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
        return row

    def active(self, task: TaskRecord) -> dict[str, Any] | None:
        if not task.active_attempt_id:
            return None
        for row in task.attempts:
            if task.active_attempt_id == string_value(row.get("attemptId", "")):
                return row
        return None

    def active_worker_id(self, task: TaskRecord) -> str:
        attempt = self.active(task)
        return "" if attempt is None else string_value(attempt.get("workerInstanceId"))

    def mark_queued(self, task: TaskRecord) -> dict[str, Any] | None:
        attempt = self.active(task)
        if attempt is None:
            return None
        now = now_iso()
        attempt.update(
            status=AttemptStatus.QUEUED.value,
            queueEnteredAt=now,
            queueLeftAt=None,
            claimedAt=None,
            startedAt=None,
            workerInstanceId="",
            finishedAt=None,
            failureMessage="",
        )
        return attempt

    def mark_running(self, task: TaskRecord, worker_instance_id: str) -> dict[str, Any] | None:
        attempt = self.active(task)
        if attempt is None:
            return None
        now = now_iso()
        attempt.update(
            status=AttemptStatus.RUNNING.value,
            workerInstanceId=worker_instance_id if worker_instance_id else "",
            claimedAt=now,
            queueLeftAt=now,
            startedAt=now,
        )
        return attempt

    def mark_finished(
        self,
        task: TaskRecord,
        status: AttemptStatus | str,
        error_message: str | None,
    ) -> tuple[dict[str, Any] | None, AttemptStatus]:
        attempt_status = status
        if isinstance(status, str):
            attempt_status = AttemptStatus._missing_(status) or AttemptStatus.FINISHED
        attempt = self.active(task)
        if attempt is not None:
            attempt["status"] = attempt_status.value
            attempt["finishedAt"] = now_iso()
            if error_message and error_message.strip():
                attempt["failureMessage"] = error_message
        return attempt, attempt_status

    def apply_transition(
        self,
        task: TaskRecord,
        transition: TaskStateTransition,
    ) -> dict[str, Any] | None:
        if task is None or transition is None or not transition.updates_attempt:
            return None
        attempt = self.active(task)
        if attempt is None:
            return None
        now = now_iso()
        status = transition.attempt_status_enum
        attempt["status"] = transition.attempt_status
        if status == AttemptStatus.QUEUED:
            attempt.update(
                queueEnteredAt=now,
                queueLeftAt=None,
                claimedAt=None,
                startedAt=None,
                workerInstanceId="",
                finishedAt=None,
                failureMessage="",
            )
        elif status == AttemptStatus.RUNNING:
            attempt.update(
                queueLeftAt=now,
                claimedAt=now,
                startedAt=now,
                finishedAt=None,
                failureMessage="",
            )
        else:
            attempt["finishedAt"] = now
            attempt["failureMessage"] = transition.attempt_error_message
        return attempt
