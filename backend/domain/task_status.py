"""Domain enums for task lifecycle tracking."""
from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    """Task execution status values."""
    PENDING = "PENDING"
    PAUSED = "PAUSED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None

    def is_running_like(self) -> bool:
        return self in (TaskStatus.ANALYZING, TaskStatus.PLANNING, TaskStatus.RENDERING)

    def is_terminal(self) -> bool:
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def is_execution_active(self) -> bool:
        return self in (TaskStatus.ANALYZING, TaskStatus.PLANNING, TaskStatus.RENDERING, TaskStatus.PENDING)


class AttemptStatus(StrEnum):
    """Attempt lifecycle status values."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


class AttemptTriggerType(StrEnum):
    """Trigger type for an attempt."""
    CREATE = "create"
    RETRY = "retry"
    CONTINUE = "continue"
    RECOVER = "recover"


class TraceLevel(StrEnum):
    """Log trace level."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"


class WorkerStatus(StrEnum):
    """Worker instance status."""
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    STALE = "STALE"


class QueueEventType(StrEnum):
    """Queue event types."""
    ENQUEUED = "enqueued"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"
    REMOVED = "removed"
    RE_ENQUEUED = "re_enqueued"


class ExecutionMode(StrEnum):
    """Execution mode."""
    QUEUE = "queue"
    DIRECT = "direct"


class UserRole(StrEnum):
    """User roles."""
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    """User account status."""
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class InviteStatus(StrEnum):
    """Invite code status."""
    UNUSED = "UNUSED"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
