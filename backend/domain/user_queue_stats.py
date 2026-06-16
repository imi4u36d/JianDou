"""User-level task queue counters for identity administration.

Mirrors the Java UserQueueStats record and UserQueueStatsProvider interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class UserQueueStats:
    """Per-user queue statistics.

    Mirrors the Java UserQueueStats record.
    """

    running_task_count: int = 0
    queued_task_count: int = 0

    @classmethod
    def empty(cls) -> UserQueueStats:
        return cls(running_task_count=0, queued_task_count=0)


@runtime_checkable
class UserQueueStatsProvider(Protocol):
    """Provides per-user task queue statistics to identity management
    without coupling it to task storage.

    Mirrors the Java UserQueueStatsProvider interface.
    """

    def list_user_queue_stats(self) -> dict[int, UserQueueStats]:
        """Return a mapping of owner_user_id -> UserQueueStats."""
        ...
