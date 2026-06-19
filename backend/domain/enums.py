from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
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


class AttemptStatus(str, Enum):
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


class AttemptTriggerType(str, Enum):
    CREATE = "create"
    RETRY = "retry"
    CONTINUE = "continue"
    RECOVER = "recover"


class StageRunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = value.strip().upper()
            aliases = {
                "PENDING": cls.RUNNING,
                "QUEUED": cls.RUNNING,
                "PROCESSING": cls.RUNNING,
                "SUCCESS": cls.COMPLETED,
                "SUCCEEDED": cls.COMPLETED,
                "ERROR": cls.FAILED,
            }
            if normalized in aliases:
                return aliases[normalized]
            for member in cls:
                if member.value == normalized:
                    return member
        return None


class TraceLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"


class WorkerStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    STALE = "STALE"


class QueueEventType(str, Enum):
    ENQUEUED = "enqueued"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"
    REMOVED = "removed"
    RE_ENQUEUED = "re_enqueued"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            lower = value.lower()
            for member in cls:
                if member.value == lower:
                    return member
        return None

    @classmethod
    def from_attempt_status(cls, status: AttemptStatus) -> QueueEventType | None:
        mapping = {
            AttemptStatus.QUEUED: cls.ENQUEUED,
            AttemptStatus.RUNNING: cls.CLAIMED,
            AttemptStatus.FINISHED: cls.COMPLETED,
            AttemptStatus.FAILED: cls.FAILED,
            AttemptStatus.TERMINATED: cls.FAILED,
            AttemptStatus.REMOVED: cls.REMOVED,
            AttemptStatus.PAUSED: cls.REMOVED,
        }
        return mapping.get(status)


class ExecutionMode(str, Enum):
    QUEUE = "queue"
    DIRECT = "direct"


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class InviteStatus(str, Enum):
    UNUSED = "UNUSED"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStage(str, Enum):
    STORYBOARD = "storyboard"
    KEYFRAME = "keyframe"
    VIDEO = "video"
    JOINED = "joined"


class WorkflowDurationMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class StageVersionStatus(str, Enum):
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    SUCCEEDED = "SUCCEEDED"
    SUCCESS = "SUCCESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
