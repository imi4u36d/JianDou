"""Worker-side operations for the persisted task queue."""

from __future__ import annotations

from typing import Any


class TaskQueueCoordinator:
    """Claims, removes, and inspects persisted queue entries."""

    SNAPSHOT_LIMIT = 500

    def __init__(self, task_repository: Any) -> None:
        self._task_repository = task_repository

    async def remove(self, task_id: str) -> None:
        await self._task_repository.remove_queued_task(task_id)

    async def claim_next(self, worker_instance_id: str) -> str | None:
        return await self._task_repository.claim_next_queued_task(worker_instance_id)

    async def snapshot(self) -> list[str]:
        return await self._task_repository.list_queued_task_ids(self.SNAPSHOT_LIMIT)
