from __future__ import annotations

from typing import Protocol


class TaskQueuePort(Protocol):
    """Port interface for the task queue.

    Implementations can be in-memory, Redis-backed, or any other system.
    """

    def enqueue(self, task_id: str) -> None: ...

    def remove(self, task_id: str) -> None: ...

    def snapshot(self) -> list[str]:
        """Return all queued task IDs in order."""
        ...


class InMemoryTaskQueue:
    """Simple in-memory FIFO queue for task IDs."""

    def __init__(self) -> None:
        self._queue: list[str] = []

    def enqueue(self, task_id: str) -> None:
        if task_id not in self._queue:
            self._queue.append(task_id)

    def remove(self, task_id: str) -> None:
        if task_id in self._queue:
            self._queue.remove(task_id)

    def snapshot(self) -> list[str]:
        return list(self._queue)
