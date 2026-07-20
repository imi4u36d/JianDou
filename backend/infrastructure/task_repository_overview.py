"""Constant-query read model for the administrative overview."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select

from backend.models.task import BizTask, BizTaskAttempt
from backend.models.user import SysUser

RUNNING_STATUSES = ("ANALYZING", "PLANNING", "RENDERING")


class TaskRepositoryOverviewService:
    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def snapshot(self) -> dict[str, Any]:
        async with self._repository._session_scope() as session:
            counts = (await session.execute(self._counts_stmt())).one()
            user_counts = (await session.execute(self._user_counts_stmt())).one()
            recent_rows = await self._recent_rows(session, None, 8)
            failure_rows = await self._recent_rows(session, ("FAILED",), 6)
            running_rows = await self._recent_rows(session, RUNNING_STATUSES, 6)
            all_rows = {row.task_id: row for row in (*recent_rows, *failure_rows, *running_rows)}
            active_attempts = await self._active_attempts(session, list(all_rows))
            queue_snapshot, queue_count = await self._queue_snapshot(session)

        queue_positions = {task_id: index + 1 for index, task_id in enumerate(queue_snapshot)}
        items_by_id = {
            task_id: self._item(row, active_attempts, queue_positions)
            for task_id, row in all_rows.items()
        }
        return {
            "counts": {
                "totalTasks": int(counts.total_tasks or 0),
                "queuedTasks": queue_count,
                "runningTasks": int(counts.running_tasks or 0),
                "completedTasks": int(counts.completed_tasks or 0),
                "failedTasks": int(counts.failed_tasks or 0),
                "highRiskTasks": 0,
                "riskyTasks": 0,
                "semanticTasks": int(counts.semantic_tasks or 0),
                "timedSemanticTasks": 0,
                "averageProgress": int(float(counts.average_progress or 0)),
                "totalUsers": int(user_counts.total_users or 0),
                "activeUsers": int(user_counts.active_users or 0),
                "adminUsers": int(user_counts.admin_users or 0),
                "disabledUsers": int(user_counts.disabled_users or 0),
            },
            "queueSnapshot": queue_snapshot,
            "recentTasks": [items_by_id[row.task_id] for row in recent_rows],
            "recentFailures": [items_by_id[row.task_id] for row in failure_rows],
            "recentRunningTasks": [items_by_id[row.task_id] for row in running_rows],
        }

    def _counts_stmt(self) -> Any:
        semantic = (
            BizTask.request_payload_json.is_not(None)
            & BizTask.request_payload_json.like('%"transcriptText"%')
            & ~BizTask.request_payload_json.like('%"transcriptText":""%')
            & ~BizTask.request_payload_json.like('%"transcriptText": ""%')
        )
        return select(
            func.count().label("total_tasks"),
            func.sum(case((BizTask.status.in_(RUNNING_STATUSES), 1), else_=0)).label("running_tasks"),
            func.sum(case((BizTask.status == "COMPLETED", 1), else_=0)).label("completed_tasks"),
            func.sum(case((BizTask.status == "FAILED", 1), else_=0)).label("failed_tasks"),
            func.sum(case((semantic, 1), else_=0)).label("semantic_tasks"),
            func.avg(func.coalesce(BizTask.progress, 0)).label("average_progress"),
        ).where(BizTask.is_deleted == 0)

    def _user_counts_stmt(self) -> Any:
        return select(
            func.count().label("total_users"),
            func.sum(case((SysUser.status == "ACTIVE", 1), else_=0)).label("active_users"),
            func.sum(case((SysUser.role == "ADMIN", 1), else_=0)).label("admin_users"),
            func.sum(case((SysUser.status == "DISABLED", 1), else_=0)).label("disabled_users"),
        )

    async def _recent_rows(self, session: Any, statuses: tuple[str, ...] | None, limit: int) -> list[Any]:
        stmt = select(
            BizTask.task_id,
            BizTask.task_type,
            BizTask.title,
            BizTask.status,
            BizTask.progress,
            BizTask.create_time,
            BizTask.update_time,
            BizTask.error_message,
        ).where(BizTask.is_deleted == 0)
        if statuses:
            stmt = stmt.where(BizTask.status.in_(statuses))
        result = await session.execute(stmt.order_by(BizTask.create_time.desc(), BizTask.id.desc()).limit(limit))
        return list(result.all())

    async def _active_attempts(self, session: Any, task_ids: list[str]) -> dict[str, Any]:
        if not task_ids:
            return {}
        stmt = (
            select(
                BizTaskAttempt.task_id,
                BizTaskAttempt.resume_from_stage,
                BizTaskAttempt.worker_instance_id,
            )
            .where(
                BizTaskAttempt.task_id.in_(task_ids),
                BizTaskAttempt.status.in_(("RUNNING", "QUEUED", "PENDING")),
                BizTaskAttempt.is_deleted == 0,
            )
            .order_by(BizTaskAttempt.attempt_no.desc())
        )
        result = await session.execute(stmt)
        active: dict[str, Any] = {}
        for row in result.all():
            active.setdefault(row.task_id, row)
        return active

    async def _queue_snapshot(self, session: Any) -> tuple[list[str], int]:
        queued = (
            BizTaskAttempt.status.in_(("QUEUED", "PENDING"))
            & (BizTaskAttempt.is_deleted == 0)
            & (BizTask.status == "PENDING")
            & (BizTask.is_deleted == 0)
        )
        base = select(BizTaskAttempt.task_id).join(BizTask, BizTask.task_id == BizTaskAttempt.task_id).where(queued)
        count_stmt = (
            select(func.count(func.distinct(BizTaskAttempt.task_id)))
            .select_from(BizTaskAttempt)
            .join(BizTask, BizTask.task_id == BizTaskAttempt.task_id)
            .where(queued)
        )
        count = int((await session.execute(count_stmt)).scalar_one() or 0)
        result = await session.execute(
            base.order_by(BizTaskAttempt.queue_entered_at.asc(), BizTask.create_time.asc()).limit(500)
        )
        return list(dict.fromkeys(row.task_id for row in result.all() if row.task_id)), count

    def _item(self, row: Any, active_attempts: dict[str, Any], queue_positions: dict[str, int]) -> dict[str, Any]:
        attempt = active_attempts.get(row.task_id)
        return {
            "id": row.task_id,
            "taskType": row.task_type or "video_generation",
            "title": row.title or "",
            "status": row.status or "",
            "progress": row.progress or 0,
            "createdAt": row.create_time or "",
            "updatedAt": row.update_time or "",
            "isQueued": row.task_id in queue_positions,
            "queuePosition": queue_positions.get(row.task_id),
            "currentStage": attempt.resume_from_stage if attempt else "",
            "activeWorkerInstanceId": attempt.worker_instance_id if attempt else "",
            "diagnosisSeverity": "",
            "failureReason": row.error_message or "",
        }
