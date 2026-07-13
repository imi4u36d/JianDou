"""Recovery workflow for attempts claimed by stale or stopped workers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.domain.enums import WorkerStatus
from backend.domain.task_record import _string_value
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation


class TaskStaleClaimRecovery:
    """Re-enqueue recoverable running attempts through a coordinator facade."""

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    async def recover(self, stale_before: datetime, limit: int, repository: Any) -> int:
        stale_cutoff = stale_before.isoformat() if hasattr(stale_before, "isoformat") else str(stale_before)
        claims = await self._await_if_needed(repository.list_stale_running_claims(stale_before, limit))
        claims = list(claims)
        if hasattr(repository, "list_orphaned_running_claims"):
            orphaned = await self._await_if_needed(repository.list_orphaned_running_claims(limit))
            claims = self._merge_claims(claims, list(orphaned))

        recovered = 0
        for claim in claims:
            if await self._recover_claim(claim, stale_cutoff, repository):
                recovered += 1
        return recovered

    async def _recover_claim(self, claim: dict[str, Any], stale_cutoff: str, repository: Any) -> bool:
        task_id = _string_value(claim.get("taskId", ""))
        if not task_id:
            return False
        task = await self._await_if_needed(repository.find_by_id(task_id))
        if task is None:
            return False
        attempt = self._coordinator._active_attempt(task)
        if attempt is None or _string_value(attempt.get("status", "")) != "RUNNING":
            return False

        worker_id = _string_value(claim.get("workerInstanceId", ""))
        if await self._worker_is_fresh(worker_id, stale_cutoff, repository):
            return False

        previous_status = task.status
        task.status = "PENDING"
        task.progress = 0
        task.error_message = ""
        task.finished_at = None
        task.is_queued = True
        task.queue_position = None
        if task.execution_context:
            context = task.mutable_execution_context()
            context["recoveredFromWorkerInstanceId"] = worker_id
            context.pop("workerInstanceId", None)

        queued_attempt = self._coordinator._mark_active_attempt_queued_in_memory(task)
        queue_event = self._coordinator._new_queue_event_row(
            task,
            "re_enqueued",
            {"reason": "stale_claim_recovered", "staleWorkerInstanceId": worker_id},
        )
        trace = self._coordinator._new_trace_row(
            "dispatch",
            "task.recovered_from_stale_claim",
            "Detected stale worker; task re-enqueued.",
            "WARN",
            {"staleWorkerInstanceId": worker_id},
        )
        history = self._coordinator._new_status_history_row(
            task,
            previous_status,
            "PENDING",
            "dispatch",
            "task.recovered_from_stale_claim",
            "Detected stale worker; task re-enqueued.",
        )
        task.add_trace(trace)
        task.add_status_history(history)
        self._coordinator._touch(task)
        mutation = (
            TaskPersistenceMutation()
            .set_task(task)
            .add_queue_event(queue_event)
            .add_trace(trace)
            .add_status_history(history)
        )
        if queued_attempt is not None:
            mutation = mutation.add_attempt(queued_attempt)
        await self._await_if_needed(repository.save_mutation(mutation))
        return True

    async def _worker_is_fresh(self, worker_id: str, stale_cutoff: str, repository: Any) -> bool:
        if not worker_id or not hasattr(repository, "find_worker_instance"):
            return False
        worker = await self._await_if_needed(repository.find_worker_instance(worker_id))
        if worker is None:
            return False
        return (
            _string_value(worker.get("status", "")) == WorkerStatus.RUNNING.value
            and _string_value(worker.get("lastHeartbeatAt", "")) >= stale_cutoff
        )

    @staticmethod
    def _merge_claims(stale: list[dict[str, Any]], orphaned: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = {_string_value(claim.get("attemptId", "")) for claim in stale}
        for claim in orphaned:
            attempt_id = _string_value(claim.get("attemptId", ""))
            if attempt_id and attempt_id in seen:
                continue
            stale.append(claim)
            if attempt_id:
                seen.add(attempt_id)
        return stale

    @staticmethod
    async def _await_if_needed(value: Any) -> Any:
        return await value if hasattr(value, "__await__") else value
