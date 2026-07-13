"""Read-model queries for lightweight task summaries and task detail responses."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.json_payloads import read_json_object
from backend.infrastructure.task_repository_detail_queries import TaskRepositoryDetailQueryService
from backend.infrastructure.task_repository_summary_support import TaskRepositorySummarySupport
from backend.models.task import BizTask, BizTaskStatusHistory
from backend.shared import string_value


class TaskRepositoryQueryService(TaskRepositorySummarySupport):
    """Executes task read models while reusing the repository session scope."""

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    def _detail_service(self) -> TaskRepositoryDetailQueryService:
        return TaskRepositoryDetailQueryService(self)

    async def list_traces(
        self,
        task_id: str | None,
        stage: str | None,
        level: str | None,
        q: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        stmt = select(BizTaskStatusHistory).where(
            BizTaskStatusHistory.operator_type == "trace",
            BizTaskStatusHistory.is_deleted == 0,
        )
        if task_id:
            stmt = stmt.where(BizTaskStatusHistory.task_id == task_id)
        if stage:
            stmt = stmt.where(BizTaskStatusHistory.stage == stage)
        if q:
            stmt = stmt.where(BizTaskStatusHistory.message.ilike(f"%{q}%"))
        stmt = stmt.order_by(BizTaskStatusHistory.change_time.desc()).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "taskId": r.task_id,
                "timestamp": r.change_time or "",
                "level": "",  # not stored in BizTaskStatusHistory
                "stage": r.stage or "",
                "event": r.event or "",
                "message": r.message or "",
                "payload": read_json_object(r.payload_json),
            }
            for r in rows
        ]

    async def list_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return lightweight task list rows without loading heavy child collections."""
        async with self._session_scope() as session:
            task_rows = await self._query_task_summary_rows(
                session,
                owner_user_id,
                q,
                status,
                sort,
                task_type,
                exclude_task_type,
                offset,
                limit,
            )
            task_ids = [row.task_id for row in task_rows]
            owner_ids = sorted({row.owner_user_id for row in task_rows if row.owner_user_id})
            owners = await self._owner_users_by_id(session, owner_ids)
            active_attempts = await self._active_attempts_by_task_id(session, task_ids)
            queue_positions = await self._queue_positions(session)
            thumbnail_urls = await self._task_thumbnail_urls_by_task_id(session, task_ids)

        items = []
        normalized_status = string_value(status).strip().upper()
        for row in task_rows:
            active_attempt = active_attempts.get(row.task_id, {})
            owner = owners.get(row.owner_user_id)
            is_queued = row.task_id in queue_positions
            if normalized_status == "QUEUED" and not is_queued:
                continue
            items.append(
                {
                    "id": row.task_id,
                    "taskType": row.task_type or "video_generation",
                    "title": row.title or "",
                    "status": row.status or "",
                    "progress": row.progress or 0,
                    "createdAt": row.create_time or "",
                    "updatedAt": row.update_time or "",
                    "sourceFileName": row.source_file_name or "",
                    "aspectRatio": row.aspect_ratio or "",
                    "minDurationSeconds": row.min_duration_seconds or 0,
                    "maxDurationSeconds": row.max_duration_seconds or 0,
                    "retryCount": row.retry_count or 0,
                    "startedAt": row.started_at,
                    "finishedAt": row.finished_at,
                    "completedOutputCount": row.output_count or 0,
                    "taskSeed": row.task_seed,
                    "effectRating": row.effect_rating,
                    "effectRatingNote": row.effect_rating_note or "",
                    "ratedAt": row.rated_at,
                    "hasTranscript": False,
                    "hasTimedTranscript": False,
                    "sourceAssetCount": 0,
                    "editingMode": row.editing_mode or "",
                    "isQueued": is_queued,
                    "queuePosition": queue_positions.get(row.task_id),
                    "currentStage": string_value(active_attempt.get("resumeFromStage")),
                    "activeWorkerInstanceId": string_value(active_attempt.get("workerInstanceId")),
                    "plannedClipCount": 0,
                    "renderedClipCount": 0,
                    "diagnosisSeverity": "",
                    "diagnosisCode": "",
                    "diagnosisHint": "",
                    "recommendedAction": "",
                    "failureReason": row.error_message or "",
                    "failureStage": "",
                    "failureClipIndex": None,
                    "thumbnailUrl": thumbnail_urls.get(row.task_id, ""),
                    "ownerUserId": row.owner_user_id,
                    "ownerUsername": owner.username if owner else None,
                    "ownerRole": owner.role if owner else None,
                }
            )
        return items

    async def count_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
    ) -> int:
        """Return the number of task summary rows matching the lightweight list filters."""
        async with self._session_scope() as session:
            stmt = select(func.count()).select_from(BizTask).where(BizTask.is_deleted == 0)
            stmt = self._apply_task_summary_filters(stmt, owner_user_id, q, status, task_type, exclude_task_type)
            result = await session.execute(stmt)
            return int(result.scalar_one() or 0)

    async def find_detail_light(self, task_id: str, owner_user_id: int | None = None) -> dict[str, Any] | None:
        return await self._detail_service().find_detail_light(task_id, owner_user_id)

    async def get_task_trace(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return await self._detail_service().get_task_trace(task_id, owner_user_id, limit)

    async def get_task_outputs_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        return await self._detail_service().get_task_outputs_light(task_id, owner_user_id, session)

    async def get_task_materials_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        return await self._detail_service().get_task_materials_light(task_id, owner_user_id, session)

    async def _query_task_summary_rows(
        self,
        session: AsyncSession,
        owner_user_id: int | None,
        q: str | None,
        status: str | None,
        sort: str | None,
        task_type: str | None,
        exclude_task_type: str | None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        stmt = select(
            BizTask.id,
            BizTask.task_id,
            BizTask.owner_user_id,
            BizTask.task_type,
            BizTask.title,
            BizTask.status,
            BizTask.progress,
            BizTask.create_time,
            BizTask.update_time,
            BizTask.source_file_name,
            BizTask.aspect_ratio,
            BizTask.min_duration_seconds,
            BizTask.max_duration_seconds,
            BizTask.output_count,
            BizTask.task_seed,
            BizTask.effect_rating,
            BizTask.effect_rating_note,
            BizTask.rated_at,
            BizTask.started_at,
            BizTask.finished_at,
            BizTask.retry_count,
            BizTask.creative_prompt,
            BizTask.editing_mode,
            BizTask.error_message,
        ).where(BizTask.is_deleted == 0)
        stmt = self._apply_task_summary_filters(stmt, owner_user_id, q, status, task_type, exclude_task_type)
        stmt = self._apply_task_summary_sort(stmt, sort)
        if offset is not None:
            stmt = stmt.offset(max(0, offset))
        if limit is not None:
            stmt = stmt.limit(max(1, limit))
        result = await session.execute(stmt)
        return list(result.all())
