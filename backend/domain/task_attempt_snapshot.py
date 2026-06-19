"""Immutable snapshot of a task attempt record.

Mirrors the Java TaskAttemptSnapshot record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.domain.enums import AttemptTriggerType, TaskStatus


@dataclass(frozen=True)
class TaskAttemptSnapshot:
    """Immutable snapshot of a task attempt.

    Mirrors the Java TaskAttemptSnapshot record. All timestamps are stored
    as ISO-format strings (or None) to keep the snapshot serializable.
    """

    attempt_id: str = ""
    task_id: str = ""
    attempt_no: int = 0
    trigger_type: str = ""
    status: TaskStatus = TaskStatus.PENDING
    queue_name: str = ""
    worker_instance_id: str = ""
    queue_entered_at: Optional[str] = None
    queue_left_at: Optional[str] = None
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    resume_from_stage: str = ""
    resume_from_clip_index: int = 0
    failure_code: str = ""
    failure_message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Ensure payload is a copy (frozen dataclass won't prevent mutation of dicts)
        if self.payload is None:
            object.__setattr__(self, "payload", {})

    @property
    def trigger_type_enum(self) -> AttemptTriggerType | None:
        """Return the trigger type as an AttemptTriggerType enum member, or None."""
        if not self.trigger_type:
            return None
        try:
            return AttemptTriggerType(self.trigger_type)
        except (ValueError, KeyError):
            return None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> TaskAttemptSnapshot:
        """Build a snapshot from a persistence row dict."""
        status_raw = row.get("status", "")
        try:
            status = TaskStatus(status_raw) if status_raw else TaskStatus.PENDING
        except (ValueError, KeyError):
            status = TaskStatus.PENDING

        return cls(
            attempt_id=str(row.get("attemptId", "") or ""),
            task_id=str(row.get("taskId", "") or ""),
            attempt_no=int(row.get("attemptNo", 0) or 0),
            trigger_type=str(row.get("triggerType", "") or ""),
            status=status,
            queue_name=str(row.get("queueName", "") or ""),
            worker_instance_id=str(row.get("workerInstanceId", "") or ""),
            queue_entered_at=row.get("queueEnteredAt"),
            queue_left_at=row.get("queueLeftAt"),
            claimed_at=row.get("claimedAt"),
            started_at=row.get("startedAt"),
            finished_at=row.get("finishedAt"),
            resume_from_stage=str(row.get("resumeFromStage", "") or ""),
            resume_from_clip_index=int(row.get("resumeFromClipIndex", 0) or 0),
            failure_code=str(row.get("failureCode", "") or ""),
            failure_message=str(row.get("failureMessage", "") or ""),
            payload=dict(row.get("payload") or {}),
        )
