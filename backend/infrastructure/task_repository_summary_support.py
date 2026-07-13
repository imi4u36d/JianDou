"""Supporting SQL queries and policies for lightweight task summaries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.json_payloads import read_json_object
from backend.infrastructure.task_repository_mapping import _first_non_blank, _looks_like_image_url
from backend.models.task import BizMaterialAsset, BizTask, BizTaskAttempt, BizTaskResult
from backend.models.user import SysUser
from backend.shared import string_value


class TaskRepositorySummarySupport:
    async def _task_thumbnail_urls_by_task_id(self, session: AsyncSession, task_ids: list[str]) -> dict[str, str]:
        if not task_ids:
            return {}
        task_id_set = {task_id for task_id in task_ids if task_id}
        scoped_task_ids = list(task_id_set)
        if not scoped_task_ids:
            return {}
        thumbnail_urls: dict[str, str] = {}
        priorities: dict[str, int] = {}

        material_stmt = (
            select(
                BizMaterialAsset.task_id,
                BizMaterialAsset.asset_role,
                BizMaterialAsset.thumbnail_url,
                BizMaterialAsset.create_time,
            )
            .where(
                BizMaterialAsset.task_id.in_(scoped_task_ids),
                BizMaterialAsset.is_deleted == 0,
                BizMaterialAsset.thumbnail_url.is_not(None),
                BizMaterialAsset.thumbnail_url != "",
            )
            .order_by(BizMaterialAsset.create_time.desc())
        )
        material_result = await session.execute(material_stmt)
        for task_id, asset_role, thumbnail_url, _create_time in material_result.all():
            normalized_task_id = string_value(task_id)
            normalized_thumbnail_url = string_value(thumbnail_url)
            if not normalized_task_id or not normalized_thumbnail_url:
                continue
            priority = 10 if string_value(asset_role).lower() == "source" else 0
            if priority < priorities.get(normalized_task_id, 99):
                thumbnail_urls[normalized_task_id] = normalized_thumbnail_url
                priorities[normalized_task_id] = priority

        missing_task_ids = task_id_set.difference(thumbnail_urls)
        if not missing_task_ids:
            return thumbnail_urls

        output_stmt = (
            select(
                BizTaskResult.task_id,
                BizTaskResult.preview_path,
                BizTaskResult.extra_json,
                BizTaskResult.clip_index,
            )
            .where(
                BizTaskResult.task_id.in_(list(missing_task_ids)),
                BizTaskResult.is_deleted == 0,
            )
            .order_by(BizTaskResult.clip_index.desc(), BizTaskResult.create_time.desc())
        )
        output_result = await session.execute(output_stmt)
        for task_id, preview_path, extra_json, _clip_index in output_result.all():
            normalized_task_id = string_value(task_id)
            if not normalized_task_id or normalized_task_id in thumbnail_urls:
                continue
            extra = read_json_object(extra_json)
            thumbnail_url = _first_non_blank(
                extra.get("thumbnailUrl"),
                extra.get("posterUrl"),
                preview_path if _looks_like_image_url(preview_path) else "",
            )
            if thumbnail_url:
                thumbnail_urls[normalized_task_id] = thumbnail_url
        return thumbnail_urls

    def _apply_task_summary_filters(
        self,
        stmt: Any,
        owner_user_id: int | None,
        q: str | None,
        status: str | None,
        task_type: str | None = None,
        exclude_task_type: str | None = None,
    ) -> Any:
        if owner_user_id is not None:
            stmt = stmt.where(BizTask.owner_user_id == owner_user_id)
        keyword = string_value(q).strip()
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    BizTask.title.ilike(like),
                    BizTask.creative_prompt.ilike(like),
                    BizTask.source_file_name.ilike(like),
                )
            )
        normalized_status = string_value(status).strip().upper()
        if normalized_status == "QUEUED":
            queued_task_ids = select(BizTaskAttempt.task_id).where(
                BizTaskAttempt.status.in_(("QUEUED", "PENDING")),
                BizTaskAttempt.is_deleted == 0,
            )
            stmt = stmt.where(BizTask.status == "PENDING", BizTask.task_id.in_(queued_task_ids))
        elif normalized_status == "ACTIVE":
            stmt = stmt.where(BizTask.status.in_(("PENDING", "ANALYZING", "PLANNING", "RENDERING", "PAUSED")))
        elif normalized_status == "PENDING":
            stmt = stmt.where(BizTask.status == "PENDING")
        elif normalized_status:
            stmt = stmt.where(BizTask.status == normalized_status)
        task_types = self._task_type_values(task_type)
        if task_types:
            stmt = stmt.where(BizTask.task_type.in_(task_types))
        excluded_task_types = self._task_type_values(exclude_task_type)
        if excluded_task_types:
            stmt = stmt.where(BizTask.task_type.notin_(excluded_task_types))
        return stmt

    def _task_type_values(self, value: str | None) -> list[str]:
        return [item.strip() for item in string_value(value).split(",") if item.strip()]

    def _apply_task_summary_sort(self, stmt: Any, sort: str | None) -> Any:
        normalized_sort = string_value(sort).strip().lower() or "created_desc"
        if normalized_sort == "created_desc":
            stmt = stmt.order_by(desc(BizTask.create_time), desc(BizTask.id))
        elif normalized_sort == "progress_desc":
            stmt = stmt.order_by(desc(BizTask.progress), desc(BizTask.update_time), desc(BizTask.id))
        elif normalized_sort == "status_desc":
            status_priority = case(
                (BizTask.status == "RENDERING", 1),
                (BizTask.status == "PLANNING", 2),
                (BizTask.status == "ANALYZING", 3),
                (BizTask.status == "PENDING", 4),
                (BizTask.status == "PAUSED", 5),
                (BizTask.status == "COMPLETED", 6),
                (BizTask.status == "FAILED", 7),
                else_=99,
            )
            stmt = stmt.order_by(status_priority.asc(), desc(BizTask.update_time), desc(BizTask.id))
        else:
            stmt = stmt.order_by(desc(BizTask.update_time), desc(BizTask.id))
        return stmt

    async def _active_attempts_by_task_id(
        self,
        session: AsyncSession,
        task_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not task_ids:
            return {}
        stmt = (
            select(BizTaskAttempt)
            .where(
                BizTaskAttempt.task_id.in_(task_ids),
                BizTaskAttempt.status.in_(("RUNNING", "QUEUED", "PENDING")),
                BizTaskAttempt.is_deleted == 0,
            )
            .order_by(BizTaskAttempt.attempt_no.desc())
        )
        result = await session.execute(stmt)
        active: dict[str, dict[str, Any]] = {}
        for row in result.scalars().all():
            if row.task_id in active:
                continue
            active[row.task_id] = {
                "attemptId": row.task_attempt_id,
                "status": row.status,
                "resumeFromStage": row.resume_from_stage or "",
                "workerInstanceId": row.worker_instance_id or "",
            }
        return active

    async def _queue_positions(self, session: AsyncSession, limit: int = 500) -> dict[str, int]:
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
        result = await session.execute(stmt)
        positions: dict[str, int] = {}
        for row in result.all():
            task_id = string_value(row[0])
            if task_id and task_id not in positions:
                positions[task_id] = len(positions) + 1
        return positions

    async def _owner_users_by_id(self, session: AsyncSession, user_ids: list[int]) -> dict[int, SysUser]:
        if not user_ids:
            return {}
        result = await session.execute(select(SysUser).where(SysUser.id.in_(user_ids)))
        return {user.id: user for user in result.scalars().all()}
