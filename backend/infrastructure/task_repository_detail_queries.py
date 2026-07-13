"""Detail and child-collection read models for one task."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.json_payloads import read_json_object
from backend.infrastructure.task_repository_detail_collections import TaskRepositoryDetailCollectionQueryService
from backend.infrastructure.task_repository_mapping import (
    _light_request_snapshot,
    _light_url,
    _material_from_row_without_metadata,
    _short_text,
)
from backend.models.task import (
    BizMaterialAsset,
    BizTask,
    BizTaskResult,
    BizTaskStatusHistory,
)
from backend.models.user import SysUser
from backend.shared import string_value

if TYPE_CHECKING:
    from backend.infrastructure.task_repository_queries import TaskRepositoryQueryService


class TaskRepositoryDetailQueryService:
    """Build lightweight detail, trace, output, and material responses."""

    def __init__(self, query_service: TaskRepositoryQueryService) -> None:
        self._query_service = query_service

    def __getattr__(self, name: str) -> Any:
        return getattr(self._query_service, name)

    def _collection_service(self) -> TaskRepositoryDetailCollectionQueryService:
        return TaskRepositoryDetailCollectionQueryService(self)

    async def find_detail_light(self, task_id: str, owner_user_id: int | None = None) -> dict[str, Any] | None:
        """Return task detail without provider request/response payloads or material metadata."""
        async with self._session_scope() as session:
            stmt = select(
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
                BizTask.error_message,
                BizTask.editing_mode,
                BizTask.creative_prompt,
                BizTask.request_payload_json,
            ).where(BizTask.task_id == task_id, BizTask.is_deleted == 0)
            if owner_user_id is not None:
                stmt = stmt.where(BizTask.owner_user_id == owner_user_id)
            result = await session.execute(stmt)
            task = result.first()
            if task is None:
                return None
            owner = await self._owner_user_by_id(session, task.owner_user_id)
            active_attempt = await self._active_attempt_row(session, task_id)
            queue_positions = await self._queue_positions(session)
            materials = await self.get_task_materials_light(task_id, owner_user_id, session=session)
            outputs = await self.get_task_outputs_light(task_id, owner_user_id, session=session)

        request_snapshot = _light_request_snapshot(read_json_object(task.request_payload_json))
        execution_context: dict[str, Any] = {}
        return {
            "id": task.task_id,
            "taskType": task.task_type or "video_generation",
            "title": task.title or "",
            "status": task.status or "",
            "progress": task.progress or 0,
            "createdAt": task.create_time or "",
            "updatedAt": task.update_time or "",
            "sourceFileName": task.source_file_name or "",
            "aspectRatio": task.aspect_ratio or "",
            "minDurationSeconds": task.min_duration_seconds or 0,
            "maxDurationSeconds": task.max_duration_seconds or 0,
            "retryCount": task.retry_count or 0,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "completedOutputCount": task.output_count or 0,
            "taskSeed": task.task_seed,
            "effectRating": task.effect_rating,
            "effectRatingNote": task.effect_rating_note or "",
            "ratedAt": task.rated_at,
            "isQueued": task.task_id in queue_positions,
            "queuePosition": queue_positions.get(task.task_id),
            "currentStage": string_value(active_attempt.get("resumeFromStage")),
            "activeWorkerInstanceId": string_value(active_attempt.get("workerInstanceId")),
            "ownerUserId": task.owner_user_id,
            "ownerUsername": owner.username if owner else None,
            "ownerRole": owner.role if owner else None,
            "ownerStatus": owner.status if owner else None,
            "errorMessage": task.error_message or "",
            "editingMode": task.editing_mode or "",
            "creativePrompt": _short_text(task.creative_prompt),
            "hasTranscript": bool(string_value(request_snapshot.get("transcriptText"))),
            "hasTimedTranscript": False,
            "sourceAssetCount": 0,
            "transcriptPreview": string_value(request_snapshot.get("transcriptText"))[:220] or None,
            "transcriptCueCount": 0,
            "executionContext": execution_context,
            "requestSnapshot": request_snapshot,
            "storyboardScript": string_value(execution_context.get("analysisScriptText")),
            "artifactDirectories": {},
            "durationDiagnostics": [],
            "plan": [],
            "trace": [],
            "statusHistory": [],
            "attempts": [active_attempt] if active_attempt else [],
            "stageRuns": [],
            "modelCalls": [],
            "materials": materials,
            "outputs": outputs,
            "sourceAssets": [],
        }

    async def get_task_trace(self, task_id: str, owner_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        async with self._session_scope() as session:
            owned = await self._task_exists(session, task_id, owner_user_id)
            if not owned:
                raise ValueError(f"Task not found: {task_id}")
            stmt = (
                select(BizTaskStatusHistory)
                .where(
                    BizTaskStatusHistory.task_id == task_id,
                    BizTaskStatusHistory.operator_type == "trace",
                    BizTaskStatusHistory.is_deleted == 0,
                )
                .order_by(BizTaskStatusHistory.change_time.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = list(reversed(result.scalars().all()))
        return [
            {
                "traceId": r.task_status_history_id,
                "timestamp": r.change_time or "",
                "level": "",
                "stage": r.stage or "",
                "event": r.event or "",
                "message": r.message or "",
                "payload": read_json_object(r.payload_json),
            }
            for r in rows
        ]

    async def get_task_outputs_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        async def load(active_session: AsyncSession) -> list[dict[str, Any]]:
            if owner_user_id is not None and not await self._task_exists(active_session, task_id, owner_user_id):
                raise ValueError(f"Task not found: {task_id}")
            stmt = (
                select(
                    BizTaskResult.task_result_id,
                    BizTaskResult.task_id,
                    BizTaskResult.result_type,
                    BizTaskResult.clip_index,
                    BizTaskResult.title,
                    BizTaskResult.reason,
                    BizTaskResult.source_model_call_id,
                    BizTaskResult.material_asset_id,
                    BizTaskResult.start_seconds,
                    BizTaskResult.end_seconds,
                    BizTaskResult.duration_seconds,
                    BizTaskResult.preview_path,
                    BizTaskResult.download_path,
                    BizTaskResult.width,
                    BizTaskResult.height,
                    BizTaskResult.mime_type,
                    BizTaskResult.size_bytes,
                    BizTaskResult.remote_url,
                    BizTaskResult.produced_at,
                )
                .where(BizTaskResult.task_id == task_id, BizTaskResult.is_deleted == 0)
                .order_by(BizTaskResult.produced_at.asc())
            )
            result = await active_session.execute(stmt)
            return [
                {
                    "resultId": r.task_result_id,
                    "taskId": r.task_id,
                    "resultType": r.result_type,
                    "clipIndex": r.clip_index,
                    "title": r.title or "",
                    "reason": r.reason or "",
                    "sourceModelCallId": r.source_model_call_id or "",
                    "materialAssetId": r.material_asset_id or "",
                    "startSeconds": r.start_seconds,
                    "endSeconds": r.end_seconds,
                    "durationSeconds": r.duration_seconds,
                    "previewPath": _light_url(r.preview_path),
                    "downloadPath": _light_url(r.download_path),
                    "width": r.width or 0,
                    "height": r.height or 0,
                    "mimeType": r.mime_type or "",
                    "sizeBytes": r.size_bytes or 0,
                    "remoteUrl": _light_url(r.remote_url),
                    "extra": {},
                    "producedAt": r.produced_at or "",
                }
                for r in result.all()
            ]

        if session is not None:
            return await load(session)
        async with self._session_scope() as scoped:
            return await load(scoped)

    async def get_task_materials_light(
        self,
        task_id: str,
        owner_user_id: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        async def load(active_session: AsyncSession) -> list[dict[str, Any]]:
            if owner_user_id is not None and not await self._task_exists(active_session, task_id, owner_user_id):
                raise ValueError(f"Task not found: {task_id}")
            stmt = (
                select(
                    BizMaterialAsset.material_asset_id,
                    BizMaterialAsset.owner_user_id,
                    BizMaterialAsset.task_id,
                    BizMaterialAsset.workflow_id,
                    BizMaterialAsset.source_task_id,
                    BizMaterialAsset.source_material_id,
                    BizMaterialAsset.asset_role,
                    BizMaterialAsset.stage_type,
                    BizMaterialAsset.clip_index,
                    BizMaterialAsset.version_no,
                    BizMaterialAsset.selected_for_next,
                    BizMaterialAsset.user_rating,
                    BizMaterialAsset.rating_note,
                    BizMaterialAsset.media_type,
                    BizMaterialAsset.title,
                    BizMaterialAsset.origin_provider,
                    BizMaterialAsset.origin_model,
                    BizMaterialAsset.remote_task_id,
                    BizMaterialAsset.remote_asset_id,
                    BizMaterialAsset.original_file_name,
                    BizMaterialAsset.stored_file_name,
                    BizMaterialAsset.file_ext,
                    BizMaterialAsset.storage_provider,
                    BizMaterialAsset.mime_type,
                    BizMaterialAsset.size_bytes,
                    BizMaterialAsset.sha256,
                    BizMaterialAsset.duration_seconds,
                    BizMaterialAsset.width,
                    BizMaterialAsset.height,
                    BizMaterialAsset.has_audio,
                    BizMaterialAsset.local_storage_path,
                    BizMaterialAsset.local_file_path,
                    BizMaterialAsset.public_url,
                    BizMaterialAsset.thumbnail_url,
                    BizMaterialAsset.third_party_url,
                    BizMaterialAsset.remote_url,
                    BizMaterialAsset.captured_at,
                    BizMaterialAsset.create_time,
                )
                .where(BizMaterialAsset.task_id == task_id, BizMaterialAsset.is_deleted == 0)
                .order_by(BizMaterialAsset.create_time.asc())
            )
            result = await active_session.execute(stmt)
            return [_material_from_row_without_metadata(row) for row in result.all()]

        if session is not None:
            return await load(session)
        async with self._session_scope() as scoped:
            return await load(scoped)

    async def _owner_user_by_id(self, session: AsyncSession, user_id: int | None) -> SysUser | None:
        if not user_id:
            return None
        owners = await self._owner_users_by_id(session, [user_id])
        return owners.get(user_id)

    async def _task_exists(self, session: AsyncSession, task_id: str, owner_user_id: int | None = None) -> bool:
        stmt = select(func.count()).select_from(BizTask).where(BizTask.task_id == task_id, BizTask.is_deleted == 0)
        if owner_user_id is not None:
            stmt = stmt.where(BizTask.owner_user_id == owner_user_id)
        result = await session.execute(stmt)
        return int(result.scalar_one() or 0) > 0

    async def _attempt_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        return await self._collection_service().attempt_rows(session, task_id)

    async def _active_attempt_row(self, session: AsyncSession, task_id: str) -> dict[str, Any]:
        return await self._collection_service().active_attempt_row(session, task_id)

    async def _status_history_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        return await self._collection_service().status_history_rows(session, task_id)

    async def _stage_run_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        return await self._collection_service().stage_run_rows(session, task_id)

    async def _model_call_rows_light(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        return await self._collection_service().model_call_rows_light(session, task_id)
