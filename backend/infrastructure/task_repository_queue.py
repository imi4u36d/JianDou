from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import or_, select

from backend.domain.json_payloads import read_json_object
from backend.models.task import BizTask, BizTaskAttempt, BizTaskQueueEvent, BizWorkerInstance
from backend.shared import now_iso, string_value

if TYPE_CHECKING:
    from backend.infrastructure.task_repository import TaskRepository


class TaskRepositoryQueueService:
    """Queue and worker persistence operations for :class:`TaskRepository`."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    async def list_queued_task_ids(self, limit: int = 500) -> list[str]:
        async with self._lock:
            stmt = (
                select(BizTaskAttempt.task_id)
                .join(BizTask, BizTask.task_id == BizTaskAttempt.task_id)
                .where(
                    BizTaskAttempt.status.in_(("QUEUED", "PENDING")),
                    BizTaskAttempt.is_deleted == 0,
                    BizTask.status == "PENDING",
                    BizTask.is_deleted == 0,
                )
                .order_by(BizTaskAttempt.queue_entered_at.asc(), BizTask.create_time.asc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            seen: list[str] = []
            for row in result.all():
                task_id = string_value(row[0])
                if task_id and task_id not in seen:
                    seen.append(task_id)
            return seen

    async def claim_next_queued_task(self, worker_instance_id: str) -> str | None:
        async with self._lock:
            try:
                stmt = (
                    select(BizTaskAttempt)
                    .join(BizTask, BizTask.task_id == BizTaskAttempt.task_id)
                    .where(
                        BizTaskAttempt.status.in_(("QUEUED", "PENDING")),
                        BizTaskAttempt.is_deleted == 0,
                        BizTask.status == "PENDING",
                        BizTask.is_deleted == 0,
                    )
                    .order_by(BizTaskAttempt.queue_entered_at.asc(), BizTask.create_time.asc())
                    .limit(1)
                )
                result = await self.session.execute(stmt)
                attempt = result.scalars().first()
                if attempt is None:
                    return None
                now = now_iso()
                attempt.status = "RUNNING"
                attempt.worker_instance_id = string_value(worker_instance_id)
                attempt.claimed_at = now
                attempt.queue_left_at = now
                attempt.update_time = now
                await self.session.flush()
                await self.session.commit()
                return string_value(attempt.task_id)
            except Exception:
                await self.session.rollback()
                raise

    async def remove_queued_task(self, task_id: str) -> None:
        async with self._lock:
            try:
                task = await self._load_task_record_without_lock(task_id)
                if task is None:
                    return
                task.is_queued = False
                task.queue_position = None
                for attempt in task.attempts:
                    if string_value(attempt.get("status")) in ("QUEUED", "PENDING"):
                        attempt["queueLeftAt"] = attempt.get("queueLeftAt") or now_iso()
                await self._save_without_lock(task)
                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    async def list_queue_events(
        self,
        task_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        stmt = select(BizTaskQueueEvent).where(BizTaskQueueEvent.is_deleted == 0)
        if task_id:
            stmt = stmt.where(BizTaskQueueEvent.task_id == task_id)
        stmt = stmt.order_by(BizTaskQueueEvent.event_time.desc()).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "taskQueueEventId": r.task_queue_event_id,
                "taskId": r.task_id,
                "attemptId": r.attempt_id or "",
                "queueName": r.queue_name or "",
                "eventType": r.event_type,
                "workerInstanceId": r.worker_instance_id or "",
                "queuePositionHint": r.queue_position_hint or 0,
                "payload": read_json_object(r.payload_json),
                "eventTime": r.event_time or "",
            }
            for r in rows
        ]

    async def list_worker_instances(self, limit: int) -> list[dict[str, Any]]:
        stmt = select(BizWorkerInstance).order_by(BizWorkerInstance.last_heartbeat_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "workerInstanceId": r.worker_instance_id,
                "workerType": r.worker_type,
                "queueName": r.queue_name or "",
                "hostName": r.host_name or "",
                "processId": r.process_id,
                "status": r.status,
                "startedAt": r.started_at or "",
                "lastHeartbeatAt": r.last_heartbeat_at or "",
                "stoppedAt": r.stopped_at or "",
                "metadata": read_json_object(r.metadata_json),
            }
            for r in rows
        ]

    async def find_worker_instance(self, worker_instance_id: str) -> dict[str, Any] | None:
        async with self._lock:
            row = await self._find_worker_row(worker_instance_id)
            if row is None:
                return None
            return {
                "workerInstanceId": row.worker_instance_id,
                "workerType": row.worker_type,
                "queueName": row.queue_name or "",
                "hostName": row.host_name or "",
                "processId": row.process_id,
                "status": row.status,
                "startedAt": row.started_at or "",
                "lastHeartbeatAt": row.last_heartbeat_at or "",
                "stoppedAt": row.stopped_at or "",
                "metadata": read_json_object(row.metadata_json),
            }

    async def list_stale_worker_instance_ids(
        self,
        stale_before: Any,
        limit: int,
    ) -> list[str]:
        stale_str = stale_before.isoformat() if hasattr(stale_before, "isoformat") else str(stale_before)
        stmt = (
            select(BizWorkerInstance.worker_instance_id)
            .where(
                BizWorkerInstance.status == "RUNNING",
                BizWorkerInstance.last_heartbeat_at < stale_str,
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def list_stale_running_claims(
        self,
        stale_before: Any,
        limit: int,
    ) -> list[dict[str, Any]]:
        stale_str = stale_before.isoformat() if hasattr(stale_before, "isoformat") else str(stale_before)
        stmt = (
            select(BizTaskAttempt)
            .where(
                BizTaskAttempt.status == "RUNNING",
                BizTaskAttempt.claimed_at < stale_str,
                BizTaskAttempt.is_deleted == 0,
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "taskId": r.task_id,
                "attemptId": r.task_attempt_id,
                "workerInstanceId": r.worker_instance_id or "",
            }
            for r in rows
        ]

    async def list_orphaned_running_claims(self, limit: int) -> list[dict[str, Any]]:
        """Find running attempts whose owning worker can no longer continue them."""
        stmt = (
            select(BizTaskAttempt)
            .outerjoin(
                BizWorkerInstance,
                BizWorkerInstance.worker_instance_id == BizTaskAttempt.worker_instance_id,
            )
            .where(
                BizTaskAttempt.status == "RUNNING",
                BizTaskAttempt.is_deleted == 0,
                or_(
                    BizTaskAttempt.worker_instance_id == "",
                    BizWorkerInstance.id.is_(None),
                    BizWorkerInstance.status != "RUNNING",
                ),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "taskId": r.task_id,
                "attemptId": r.task_attempt_id,
                "workerInstanceId": r.worker_instance_id or "",
            }
            for r in rows
        ]

    async def list_user_queue_stats(self) -> list[dict[str, Any]]:
        """Aggregate queue stats per owner. Simplified implementation."""
        # In a real impl this would be a GROUP BY query.
        # For now return empty until the query becomes needed.
        return []
