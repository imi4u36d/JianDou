from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import case, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_factory
from backend.domain.enums import StageRunStatus
from backend.domain.json_payloads import object_value, read_json_object, write_json_object
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.models.task import (
    BizMaterialAsset,
    BizTask,
    BizTaskAttempt,
    BizTaskModelCall,
    BizTaskQueueEvent,
    BizTaskResult,
    BizTaskStageRun,
    BizTaskStatusHistory,
    BizWorkerInstance,
)
from backend.models.user import SysUser
from backend.services.provider_payload_sanitizer import ProviderPayloadSanitizer
from backend.shared import now_iso, safe_int, string_value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def _stage_run_status(value: Any) -> str:
    status = StageRunStatus._missing_(string_value(value))
    return status.value if status is not None else StageRunStatus.FAILED.value


def _first_non_blank(*values: Any) -> str:
    for value in values:
        normalized = string_value(value).strip()
        if normalized:
            return normalized
    return ""


def _material_public_url_from_row(row: BizMaterialAsset) -> str:
    return _first_non_blank(row.public_url, row.remote_url, row.third_party_url)


def _material_public_url_from_payload(row: dict[str, Any]) -> str:
    return _first_non_blank(row.get("publicUrl"), row.get("fileUrl"), row.get("remoteUrl"), row.get("thirdPartyUrl"))


def _material_thumbnail_url_from_payload(row: dict[str, Any]) -> str:
    return _first_non_blank(row.get("thumbnailUrl"), row.get("previewUrl"))


# ---------------------------------------------------------------------------
# Mapping helpers: TaskRecord <-> BizTask
# ---------------------------------------------------------------------------


def _biz_task_from_record(record: TaskRecord) -> BizTask:
    """Convert a TaskRecord into a BizTask ORM instance."""
    return BizTask(
        task_id=record.id,
        owner_user_id=record.owner_user_id or 0,
        task_type=record.task_type or "video_generation",
        title=record.title or "",
        description=None,
        aspect_ratio=record.aspect_ratio or "",
        min_duration_seconds=record.min_duration_seconds or 0,
        max_duration_seconds=record.max_duration_seconds or 0,
        output_count=record.completed_output_count or 0,
        source_primary_asset_id="",
        source_file_name=record.source_file_name or "",
        source_asset_ids_json=None,
        source_file_names_json=None,
        request_payload_json=write_json_object(record.request_snapshot) if record.request_snapshot else None,
        context_json=write_json_object(record.execution_context) if record.execution_context else None,
        intro_template=record.intro_template or "",
        outro_template=record.outro_template or "",
        creative_prompt=record.creative_prompt,
        task_seed=record.task_seed,
        effect_rating=record.effect_rating,
        effect_rating_note=record.effect_rating_note or "",
        rated_at=record.rated_at,
        model_provider="",
        execution_mode="",
        editing_mode=record.editing_mode or "",
        status=record.status or "",
        progress=record.progress or 0,
        error_code="",
        error_message=record.error_message,
        plan_json=None,
        retry_count=record.retry_count or 0,
        timezone_offset_minutes=0,
        started_at=record.started_at,
        finished_at=record.finished_at,
        create_time=record.created_at or "",
        update_time=record.updated_at or "",
        is_deleted=0,
        remark="",
    )


def _material_from_row(row: BizMaterialAsset) -> dict[str, Any]:
    metadata = read_json_object(row.metadata_json)
    public_url = _material_public_url_from_row(row)
    thumbnail_url = row.thumbnail_url or ""
    return {
        "id": row.material_asset_id,
        "materialAssetId": row.material_asset_id,
        "ownerUserId": row.owner_user_id,
        "taskId": row.task_id or "",
        "workflowId": row.workflow_id or "",
        "sourceTaskId": row.source_task_id or "",
        "sourceMaterialId": row.source_material_id or "",
        "kind": row.asset_role or "",
        "assetRole": row.asset_role or "",
        "stageType": row.stage_type or "",
        "clipIndex": row.clip_index or 0,
        "versionNo": row.version_no,
        "selectedForNext": row.selected_for_next or 0,
        "userRating": row.user_rating,
        "ratingNote": row.rating_note or "",
        "mediaType": row.media_type or "",
        "title": row.title or "",
        "originProvider": row.origin_provider or "",
        "originModel": row.origin_model or "",
        "remoteTaskId": row.remote_task_id or "",
        "remoteAssetId": row.remote_asset_id or "",
        "originalFileName": row.original_file_name or "",
        "storedFileName": row.stored_file_name or "",
        "fileExt": row.file_ext or "",
        "storageProvider": row.storage_provider or "",
        "mimeType": row.mime_type or "",
        "sizeBytes": row.size_bytes or 0,
        "sha256": row.sha256 or "",
        "durationSeconds": row.duration_seconds or 0,
        "width": row.width or 0,
        "height": row.height or 0,
        "hasAudio": bool(row.has_audio),
        "storagePath": row.local_storage_path or "",
        "localFilePath": row.local_file_path or "",
        "publicUrl": public_url,
        "fileUrl": public_url,
        "previewUrl": thumbnail_url,
        "thumbnailUrl": thumbnail_url,
        "thirdPartyUrl": "",
        "remoteUrl": "",
        "metadata": metadata,
        "createdAt": row.captured_at or row.create_time or "",
    }


def _material_from_row_without_metadata(row: BizMaterialAsset) -> dict[str, Any]:
    public_url = _material_public_url_from_row(row)
    thumbnail_url = row.thumbnail_url or ""
    return {
        "id": row.material_asset_id,
        "materialAssetId": row.material_asset_id,
        "ownerUserId": row.owner_user_id,
        "taskId": row.task_id or "",
        "workflowId": row.workflow_id or "",
        "sourceTaskId": row.source_task_id or "",
        "sourceMaterialId": row.source_material_id or "",
        "kind": row.asset_role or "",
        "assetRole": row.asset_role or "",
        "stageType": row.stage_type or "",
        "clipIndex": row.clip_index or 0,
        "versionNo": row.version_no,
        "selectedForNext": row.selected_for_next or 0,
        "userRating": row.user_rating,
        "ratingNote": row.rating_note or "",
        "mediaType": row.media_type or "",
        "title": row.title or "",
        "originProvider": row.origin_provider or "",
        "originModel": row.origin_model or "",
        "remoteTaskId": row.remote_task_id or "",
        "remoteAssetId": row.remote_asset_id or "",
        "originalFileName": row.original_file_name or "",
        "storedFileName": row.stored_file_name or "",
        "fileExt": row.file_ext or "",
        "storageProvider": row.storage_provider or "",
        "mimeType": row.mime_type or "",
        "sizeBytes": row.size_bytes or 0,
        "sha256": row.sha256 or "",
        "durationSeconds": row.duration_seconds or 0,
        "width": row.width or 0,
        "height": row.height or 0,
        "hasAudio": bool(row.has_audio),
        "storagePath": row.local_storage_path or "",
        "localFilePath": row.local_file_path or "",
        "publicUrl": public_url,
        "fileUrl": public_url,
        "previewUrl": thumbnail_url,
        "thumbnailUrl": thumbnail_url,
        "thirdPartyUrl": "",
        "remoteUrl": "",
        "metadata": {},
        "createdAt": row.captured_at or row.create_time or "",
    }


def _record_from_biz_task(row: BizTask) -> TaskRecord:
    """Convert a BizTask ORM row into a TaskRecord."""
    request_snapshot = read_json_object(row.request_payload_json)
    execution_context = read_json_object(row.context_json)

    rec = TaskRecord(
        id=row.task_id or "",
        owner_user_id=row.owner_user_id,
        task_type=row.task_type or "video_generation",
        title=row.title or "",
        aspect_ratio=row.aspect_ratio or "",
        min_duration_seconds=row.min_duration_seconds or 8,
        max_duration_seconds=row.max_duration_seconds or 8,
        retry_count=row.retry_count or 0,
        started_at=row.started_at,
        finished_at=row.finished_at,
        completed_output_count=safe_int(execution_context.get("completedOutputCount"), 0),
        current_attempt_no=0,
        has_transcript=bool(string_value(request_snapshot.get("transcriptText"))),
        has_timed_transcript=False,
        source_asset_count=0,
        editing_mode=row.editing_mode or "",
        is_queued=False,
        queue_position=None,
        active_attempt_id="",
        intro_template=row.intro_template or "",
        outro_template=row.outro_template or "",
        creative_prompt=row.creative_prompt or "",
        task_seed=row.task_seed,
        effect_rating=row.effect_rating,
        effect_rating_note=row.effect_rating_note or "",
        rated_at=row.rated_at,
        error_message=row.error_message or "",
        transcript_text=string_value(request_snapshot.get("transcriptText")),
        storyboard_script=string_value(execution_context.get("analysisScriptText")),
        status=row.status or "",
        progress=row.progress or 0,
        created_at=row.create_time or "",
        updated_at=row.update_time or "",
        source_file_name=row.source_file_name or "",
        execution_context=execution_context,
        request_snapshot=request_snapshot,
    )
    return rec


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


# =============================================================================
# TASK REPOSITORY
# =============================================================================
class TaskRepository:
    """SQLAlchemy-based repository for TaskRecord aggregates.

    Mirrors the Java MybatisTaskRepository.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._uses_external_session = session is not None
        self._lock = asyncio.Lock()

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            self._session = async_session_factory()
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    @asynccontextmanager
    async def _session_scope(self):
        if self._uses_external_session and self._session is not None:
            yield self._session
            return
        async with async_session_factory() as session:
            yield session

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def _find_task_row(self, task_id: str) -> BizTask | None:
        result = await self.session.execute(
            select(BizTask).where(
                BizTask.task_id == task_id,
                BizTask.is_deleted == 0,
            )
        )
        return result.scalars().first()

    async def _find_attempt_row(self, attempt_id: str) -> BizTaskAttempt | None:
        result = await self.session.execute(select(BizTaskAttempt).where(BizTaskAttempt.task_attempt_id == attempt_id))
        return result.scalars().first()

    async def _find_worker_row(self, worker_instance_id: str) -> BizWorkerInstance | None:
        result = await self.session.execute(
            select(BizWorkerInstance).where(BizWorkerInstance.worker_instance_id == worker_instance_id)
        )
        return result.scalars().first()

    async def _find_material_row(self, material_asset_id: str) -> BizMaterialAsset | None:
        result = await self.session.execute(
            select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == material_asset_id)
        )
        return result.scalars().first()

    async def _load_task_record_without_lock(self, task_id: str) -> TaskRecord | None:
        row = await self._find_task_row(task_id)
        if row is None:
            return None
        rec = _record_from_biz_task(row)
        await self._load_sub_collections(rec)
        return rec

    async def _save_without_lock(self, task_record: TaskRecord) -> None:
        row = _biz_task_from_record(task_record)
        existing = await self._find_task_row(task_record.id)
        if existing:
            for col in BizTask.__table__.columns:
                col_name = col.name
                if col_name in {"id", "task_id"}:
                    continue
                if hasattr(row, col_name):
                    setattr(existing, col_name, getattr(row, col_name))
        else:
            self.session.add(row)

    async def save(self, task_record: TaskRecord) -> None:
        """Upsert the main task row."""
        async with self._lock:
            try:
                await self._save_without_lock(task_record)
                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        """Persist a full mutation atomically (task + sub-entities)."""
        async with self._lock:
            try:
                # 1. Task main row
                if mutation.task:
                    await self._save_without_lock(mutation.task)

                task_id = mutation.task_id or (mutation.task.id if mutation.task else "")

                # 2. Attempts (upsert by task_attempt_id)
                for row in mutation.attempts:
                    await self._upsert_attempt(task_id, row)

                # 3. Status history
                for row in mutation.status_history_rows:
                    self.session.add(
                        BizTaskStatusHistory(
                            task_status_history_id=string_value(row.get("statusHistoryId", row.get("id", ""))),
                            task_id=task_id,
                            previous_status=string_value(row.get("previousStatus", "")),
                            current_status=string_value(row.get("nextStatus", "")),
                            progress=safe_int(row.get("progress")),
                            stage=string_value(row.get("stage")),
                            event=string_value(row.get("event")),
                            message=string_value(row.get("reason", row.get("message", ""))),
                            payload_json=write_json_object(row.get("payload", {})),
                            change_time=string_value(row.get("changedAt", row.get("timestamp", now_iso()))),
                            operator_type="system",
                            operator_id="",
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 4. Trace rows -> store as BizTaskStatusHistory with special event prefix
                for row in mutation.trace_rows:
                    self.session.add(
                        BizTaskStatusHistory(
                            task_status_history_id=string_value(row.get("traceId", row.get("id", ""))),
                            task_id=task_id,
                            previous_status="",
                            current_status="",
                            progress=0,
                            stage=string_value(row.get("stage")),
                            event=string_value(row.get("event")),
                            message=string_value(row.get("message")),
                            payload_json=write_json_object(row.get("payload", {})),
                            change_time=string_value(row.get("timestamp", now_iso())),
                            operator_type="trace",
                            operator_id="",
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 5. Stage runs
                for row in mutation.stage_run_rows:
                    await self._upsert_stage_run(task_id, row)

                # 6. Model calls
                for row in mutation.model_call_rows:
                    await self._upsert_model_call(task_id, row)

                # 7. Materials
                for row in mutation.material_rows:
                    await self._upsert_material_asset(task_id, mutation.task, row)

                # 8. Results
                for row in mutation.result_rows:
                    self.session.add(
                        BizTaskResult(
                            task_result_id=string_value(row.get("resultId", row.get("id", ""))),
                            task_id=task_id,
                            result_type=string_value(row.get("resultType", "")),
                            clip_index=safe_int(row.get("clipIndex"), 0),
                            title=string_value(row.get("title", "")),
                            reason=string_value(row.get("reason", "")),
                            source_model_call_id=string_value(row.get("sourceModelCallId", "")),
                            material_asset_id=string_value(row.get("materialAssetId", "")),
                            start_seconds=float(row.get("startSeconds") or 0),
                            end_seconds=float(row.get("endSeconds") or 0),
                            duration_seconds=float(row.get("durationSeconds") or 0),
                            preview_path=string_value(row.get("previewPath", row.get("previewUrl", ""))),
                            download_path=string_value(row.get("downloadPath", row.get("downloadUrl", ""))),
                            width=safe_int(row.get("width"), 0),
                            height=safe_int(row.get("height"), 0),
                            mime_type=string_value(row.get("mimeType", "")),
                            size_bytes=safe_int(row.get("sizeBytes"), 0),
                            remote_url=string_value(row.get("remoteUrl", "")),
                            extra_json=write_json_object(row.get("extra", {})),
                            produced_at=string_value(row.get("producedAt", now_iso())),
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 9. Queue events
                for row in mutation.queue_event_rows:
                    self.session.add(
                        BizTaskQueueEvent(
                            task_queue_event_id=string_value(row.get("taskQueueEventId", row.get("id", ""))),
                            task_id=task_id,
                            attempt_id=string_value(row.get("attemptId", "")),
                            queue_name=string_value(row.get("queueName", "default")),
                            event_type=string_value(row.get("eventType", "")),
                            worker_instance_id=string_value(row.get("workerInstanceId", "")),
                            queue_position_hint=safe_int(row.get("queuePositionHint"), 0),
                            payload_json=write_json_object(row.get("payload", {})),
                            event_time=string_value(row.get("eventTime", now_iso())),
                            timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                            create_time=now_iso(),
                            update_time=now_iso(),
                            is_deleted=0,
                            remark="",
                        )
                    )

                # 10. Worker instances (upsert)
                for row in mutation.worker_instance_rows:
                    await self._upsert_worker_instance(row)

                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    async def find_by_id(self, task_id: str) -> TaskRecord | None:
        """Load a task with all related sub-collections."""
        async with self._lock:
            return await self._load_task_record_without_lock(task_id)

    async def list_task_summaries(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return lightweight task list rows without loading heavy child collections."""
        async with self._session_scope() as session:
            task_rows = await self._query_task_summary_rows(session, owner_user_id, q, status, sort)
            task_ids = [row.task_id for row in task_rows]
            owner_ids = sorted({row.owner_user_id for row in task_rows if row.owner_user_id})
            owners = await self._owner_users_by_id(session, owner_ids)
            active_attempts = await self._active_attempts_by_task_id(session, task_ids)
            queue_positions = await self._queue_positions(session)

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
                    "thumbnailUrl": "",
                    "ownerUserId": row.owner_user_id,
                    "ownerUsername": owner.username if owner else None,
                    "ownerRole": owner.role if owner else None,
                }
            )
        return items

    async def find_detail_light(self, task_id: str, owner_user_id: int | None = None) -> dict[str, Any] | None:
        """Return task detail without provider request/response payloads or material metadata."""
        async with self._session_scope() as session:
            stmt = select(BizTask).where(BizTask.task_id == task_id, BizTask.is_deleted == 0)
            if owner_user_id is not None:
                stmt = stmt.where(BizTask.owner_user_id == owner_user_id)
            result = await session.execute(stmt)
            task = result.scalars().first()
            if task is None:
                return None
            owner = await self._owner_user_by_id(session, task.owner_user_id)
            attempts = await self._attempt_rows(session, task_id)
            active_attempt = next(
                (row for row in attempts if string_value(row.get("status")) in ("RUNNING", "QUEUED", "PENDING")),
                {},
            )
            queue_positions = await self._queue_positions(session)
            status_history = await self._status_history_rows(session, task_id)
            stage_runs = await self._stage_run_rows(session, task_id)
            model_calls = await self._model_call_rows_light(session, task_id)
            materials = await self.get_task_materials_light(task_id, owner_user_id, session=session)
            outputs = await self.get_task_outputs_light(task_id, owner_user_id, session=session)

        request_snapshot = read_json_object(task.request_payload_json)
        execution_context = read_json_object(task.context_json)
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
            "creativePrompt": task.creative_prompt or "",
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
            "statusHistory": status_history,
            "attempts": attempts,
            "stageRuns": stage_runs,
            "modelCalls": model_calls,
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
                    "previewPath": r.preview_path or "",
                    "downloadPath": r.download_path or "",
                    "width": r.width or 0,
                    "height": r.height or 0,
                    "mimeType": r.mime_type or "",
                    "sizeBytes": r.size_bytes or 0,
                    "remoteUrl": r.remote_url or "",
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

    async def _query_task_summary_rows(
        self,
        session: AsyncSession,
        owner_user_id: int | None,
        q: str | None,
        status: str | None,
        sort: str | None,
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
        if normalized_status and normalized_status != "QUEUED":
            stmt = stmt.where(BizTask.status == normalized_status)

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
        result = await session.execute(stmt)
        return list(result.all())

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
        stmt = (
            select(BizTaskAttempt)
            .where(BizTaskAttempt.task_id == task_id, BizTaskAttempt.is_deleted == 0)
            .order_by(BizTaskAttempt.attempt_no.desc())
        )
        result = await session.execute(stmt)
        rows = []
        for a in result.scalars().all():
            rows.append(
                {
                    "attemptId": a.task_attempt_id,
                    "taskId": a.task_id,
                    "attemptNo": a.attempt_no,
                    "triggerType": a.trigger_type or "",
                    "status": a.status,
                    "queueName": a.queue_name or "",
                    "workerInstanceId": a.worker_instance_id or "",
                    "queueEnteredAt": a.queue_entered_at,
                    "queueLeftAt": a.queue_left_at,
                    "claimedAt": a.claimed_at,
                    "startedAt": a.started_at,
                    "finishedAt": a.finished_at,
                    "resumeFromStage": a.resume_from_stage or "",
                    "resumeFromClipIndex": a.resume_from_clip_index or 0,
                    "failureCode": a.failure_code or "",
                    "failureMessage": a.failure_message or "",
                    "payload": read_json_object(a.payload_json),
                }
            )
        return rows

    async def _status_history_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(BizTaskStatusHistory)
            .where(
                BizTaskStatusHistory.task_id == task_id,
                BizTaskStatusHistory.operator_type != "trace",
                BizTaskStatusHistory.is_deleted == 0,
            )
            .order_by(BizTaskStatusHistory.change_time.asc())
        )
        result = await session.execute(stmt)
        return [
            {
                "statusHistoryId": r.task_status_history_id,
                "taskId": r.task_id,
                "previousStatus": r.previous_status or "",
                "nextStatus": r.current_status or "",
                "progress": r.progress or 0,
                "stage": r.stage or "",
                "event": r.event or "",
                "reason": r.message or "",
                "operator": r.operator_type or "",
                "changedAt": r.change_time or "",
                "payload": read_json_object(r.payload_json),
            }
            for r in result.scalars().all()
        ]

    async def _stage_run_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(BizTaskStageRun)
            .where(BizTaskStageRun.task_id == task_id, BizTaskStageRun.is_deleted == 0)
            .order_by(BizTaskStageRun.stage_seq.asc(), BizTaskStageRun.clip_index.asc())
        )
        result = await session.execute(stmt)
        return [
            {
                "stageRunId": r.task_stage_run_id,
                "taskId": r.task_id,
                "attemptId": r.attempt_id or "",
                "stageName": r.stage_name or "",
                "stageSeq": r.stage_seq or 0,
                "clipIndex": r.clip_index or 0,
                "status": r.status or "",
                "workerInstanceId": r.worker_instance_id or "",
                "startedAt": r.started_at or "",
                "finishedAt": r.finished_at,
                "durationMs": r.duration_ms or 0,
                "inputSummary": read_json_object(r.input_summary_json),
                "outputSummary": read_json_object(r.output_summary_json),
                "errorCode": r.error_code or "",
                "errorMessage": r.error_message or "",
            }
            for r in result.scalars().all()
        ]

    async def _model_call_rows_light(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(
                BizTaskModelCall.task_model_call_id,
                BizTaskModelCall.task_id,
                BizTaskModelCall.call_kind,
                BizTaskModelCall.stage,
                BizTaskModelCall.operation,
                BizTaskModelCall.provider,
                BizTaskModelCall.provider_model,
                BizTaskModelCall.requested_model,
                BizTaskModelCall.resolved_model,
                BizTaskModelCall.model_name,
                BizTaskModelCall.model_alias,
                BizTaskModelCall.endpoint_host,
                BizTaskModelCall.request_id,
                BizTaskModelCall.http_status,
                BizTaskModelCall.response_status_code,
                BizTaskModelCall.success,
                BizTaskModelCall.error_code,
                BizTaskModelCall.error_message,
                BizTaskModelCall.latency_ms,
                BizTaskModelCall.duration_ms,
                BizTaskModelCall.input_tokens,
                BizTaskModelCall.output_tokens,
                BizTaskModelCall.started_at,
                BizTaskModelCall.finished_at,
            )
            .where(BizTaskModelCall.task_id == task_id, BizTaskModelCall.is_deleted == 0)
            .order_by(BizTaskModelCall.create_time.asc())
        )
        result = await session.execute(stmt)
        return [
            {
                "modelCallId": row.task_model_call_id,
                "taskId": row.task_id,
                "callKind": row.call_kind or "",
                "stage": row.stage or "",
                "operation": row.operation or "",
                "provider": row.provider or "",
                "providerModel": row.provider_model or "",
                "requestedModel": row.requested_model or "",
                "resolvedModel": row.resolved_model or "",
                "modelName": row.model_name or "",
                "modelAlias": row.model_alias or "",
                "endpointHost": row.endpoint_host or "",
                "requestId": row.request_id or "",
                "requestPayload": {},
                "responsePayload": {},
                "httpStatus": row.http_status or 0,
                "responseStatusCode": row.response_status_code or 0,
                "success": row.success or 0,
                "errorCode": row.error_code or "",
                "errorMessage": row.error_message or "",
                "latencyMs": row.latency_ms or 0,
                "durationMs": row.duration_ms or 0,
                "inputTokens": row.input_tokens or 0,
                "outputTokens": row.output_tokens or 0,
                "startedAt": row.started_at or "",
                "finishedAt": row.finished_at or "",
            }
            for row in result.all()
        ]

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

    async def find_all(self) -> list[TaskRecord]:
        """Load all non-deleted tasks."""
        async with self._lock:
            stmt = select(BizTask).where(BizTask.is_deleted == 0).order_by(BizTask.create_time.desc())
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            records = [_record_from_biz_task(r) for r in rows]
            for rec in records:
                await self._load_sub_collections(rec)
            return records

    async def delete(self, task_id: str) -> None:
        """Soft delete a task."""
        async with self._lock:
            try:
                stmt = update(BizTask).where(BizTask.task_id == task_id).values(is_deleted=1, update_time=now_iso())
                await self.session.execute(stmt)
                await self.session.flush()
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    # ------------------------------------------------------------------
    # Query helpers (matching Java TaskPersistencePort)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_sub_collections(self, rec: TaskRecord) -> None:
        """Load all sub-collections for a TaskRecord from DB."""
        tid = rec.id
        if not tid:
            return

        # Load attempts
        stmt = (
            select(BizTaskAttempt)
            .where(BizTaskAttempt.task_id == tid, BizTaskAttempt.is_deleted == 0)
            .order_by(BizTaskAttempt.attempt_no.desc())
        )
        result = await self.session.execute(stmt)
        for a in result.scalars().all():
            payload = read_json_object(a.payload_json)
            rec.attempts.append(
                {
                    "attemptId": a.task_attempt_id,
                    "taskId": a.task_id,
                    "attemptNo": a.attempt_no,
                    "triggerType": a.trigger_type or "",
                    "status": a.status,
                    "queueName": a.queue_name or "",
                    "workerInstanceId": a.worker_instance_id or "",
                    "queueEnteredAt": a.queue_entered_at,
                    "queueLeftAt": a.queue_left_at,
                    "claimedAt": a.claimed_at,
                    "startedAt": a.started_at,
                    "finishedAt": a.finished_at,
                    "resumeFromStage": a.resume_from_stage or "",
                    "resumeFromClipIndex": a.resume_from_clip_index or 0,
                    "failureCode": a.failure_code or "",
                    "failureMessage": a.failure_message or "",
                    "payload": payload,
                }
            )
            if a.status in ("RUNNING", "QUEUED", "PENDING"):
                rec.active_attempt_id = a.task_attempt_id
                rec.current_attempt_no = a.attempt_no
            if a.status in ("QUEUED", "PENDING"):
                rec.is_queued = True
                rec.queue_position = 1 if rec.queue_position is None else rec.queue_position

        # Load status history (trace rows from BizTaskStatusHistory)
        stmt = (
            select(BizTaskStatusHistory)
            .where(
                BizTaskStatusHistory.task_id == tid,
                BizTaskStatusHistory.operator_type == "trace",
                BizTaskStatusHistory.is_deleted == 0,
            )
            .order_by(BizTaskStatusHistory.change_time.asc())
        )
        result = await self.session.execute(stmt)
        for r in result.scalars().all():
            payload = read_json_object(r.payload_json)
            rec.trace.append(
                {
                    "traceId": r.task_status_history_id,
                    "timestamp": r.change_time or "",
                    "level": "",
                    "stage": r.stage or "",
                    "event": r.event or "",
                    "message": r.message or "",
                    "payload": payload,
                }
            )

        # Load status history (non-trace)
        stmt = (
            select(BizTaskStatusHistory)
            .where(
                BizTaskStatusHistory.task_id == tid,
                BizTaskStatusHistory.operator_type != "trace",
                BizTaskStatusHistory.is_deleted == 0,
            )
            .order_by(BizTaskStatusHistory.change_time.asc())
        )
        result = await self.session.execute(stmt)
        for r in result.scalars().all():
            payload = read_json_object(r.payload_json)
            rec.status_history.append(
                {
                    "statusHistoryId": r.task_status_history_id,
                    "taskId": r.task_id,
                    "previousStatus": r.previous_status or "",
                    "nextStatus": r.current_status or "",
                    "progress": r.progress or 0,
                    "stage": r.stage or "",
                    "event": r.event or "",
                    "reason": r.message or "",
                    "operator": r.operator_type or "",
                    "changedAt": r.change_time or "",
                    "payload": payload,
                }
            )

        # Load model calls
        stmt = (
            select(BizTaskModelCall)
            .where(BizTaskModelCall.task_id == tid, BizTaskModelCall.is_deleted == 0)
            .order_by(BizTaskModelCall.create_time.asc())
        )
        result = await self.session.execute(stmt)
        for m in result.scalars().all():
            req_payload = read_json_object(m.request_payload_json)
            resp_payload = read_json_object(m.response_payload_json)
            rec.model_calls.append(
                {
                    "modelCallId": m.task_model_call_id,
                    "taskId": m.task_id,
                    "callKind": m.call_kind or "",
                    "stage": m.stage or "",
                    "operation": m.operation or "",
                    "provider": m.provider or "",
                    "providerModel": m.provider_model or "",
                    "requestedModel": m.requested_model or "",
                    "resolvedModel": m.resolved_model or "",
                    "modelName": m.model_name or "",
                    "modelAlias": m.model_alias or "",
                    "endpointHost": m.endpoint_host or "",
                    "requestId": m.request_id or "",
                    "requestPayload": req_payload,
                    "responsePayload": resp_payload,
                    "httpStatus": m.http_status or 0,
                    "responseStatusCode": m.response_status_code or 0,
                    "success": m.success or 0,
                    "errorCode": m.error_code or "",
                    "errorMessage": m.error_message or "",
                    "latencyMs": m.latency_ms or 0,
                    "durationMs": m.duration_ms or 0,
                    "inputTokens": m.input_tokens or 0,
                    "outputTokens": m.output_tokens or 0,
                    "startedAt": m.started_at or "",
                    "finishedAt": m.finished_at or "",
                }
            )

        # Load materials
        stmt = (
            select(BizMaterialAsset)
            .where(BizMaterialAsset.task_id == tid, BizMaterialAsset.is_deleted == 0)
            .order_by(BizMaterialAsset.create_time.asc())
        )
        result = await self.session.execute(stmt)
        for asset in result.scalars().all():
            rec.materials.append(_material_from_row(asset))

        # Load results
        stmt = (
            select(BizTaskResult)
            .where(BizTaskResult.task_id == tid, BizTaskResult.is_deleted == 0)
            .order_by(BizTaskResult.produced_at.asc())
        )
        result = await self.session.execute(stmt)
        for r in result.scalars().all():
            extra = read_json_object(r.extra_json)
            rec.outputs.append(
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
                    "previewPath": r.preview_path or "",
                    "downloadPath": r.download_path or "",
                    "width": r.width or 0,
                    "height": r.height or 0,
                    "mimeType": r.mime_type or "",
                    "sizeBytes": r.size_bytes or 0,
                    "remoteUrl": r.remote_url or "",
                    "extra": extra,
                    "producedAt": r.produced_at or "",
                }
            )

    async def _upsert_attempt(self, task_id: str, row: dict[str, Any]) -> None:
        attempt_id = string_value(row.get("attemptId", ""))
        if not attempt_id:
            return
        existing = await self._find_attempt_row(attempt_id)
        safe_payload = object_value(row.get("payload", {}))
        if existing:
            existing.status = string_value(row.get("status", existing.status))
            existing.trigger_type = string_value(row.get("triggerType", existing.trigger_type))
            existing.queue_name = string_value(row.get("queueName", existing.queue_name))
            existing.worker_instance_id = string_value(row.get("workerInstanceId", existing.worker_instance_id))
            existing.queue_entered_at = row.get("queueEnteredAt", existing.queue_entered_at)
            existing.queue_left_at = row.get("queueLeftAt", existing.queue_left_at)
            existing.claimed_at = row.get("claimedAt", existing.claimed_at)
            existing.started_at = row.get("startedAt", existing.started_at)
            existing.finished_at = row.get("finishedAt", existing.finished_at)
            existing.resume_from_stage = string_value(row.get("resumeFromStage", existing.resume_from_stage))
            existing.resume_from_clip_index = safe_int(
                row.get("resumeFromClipIndex"), existing.resume_from_clip_index or 0
            )
            existing.failure_code = string_value(row.get("failureCode", existing.failure_code))
            existing.failure_message = string_value(row.get("failureMessage", existing.failure_message))
            existing.payload_json = write_json_object(safe_payload)
            existing.timezone_offset_minutes = safe_int(
                row.get("timezoneOffsetMinutes"), existing.timezone_offset_minutes or 0
            )
            existing.update_time = now_iso()
        else:
            self.session.add(
                BizTaskAttempt(
                    task_attempt_id=attempt_id,
                    task_id=task_id,
                    attempt_no=max(1, safe_int(row.get("attemptNo"), 1)),
                    trigger_type=string_value(row.get("triggerType", "")),
                    status=string_value(row.get("status", "")),
                    queue_name=string_value(row.get("queueName", "default")),
                    worker_instance_id=string_value(row.get("workerInstanceId", "")),
                    queue_entered_at=row.get("queueEnteredAt"),
                    queue_left_at=row.get("queueLeftAt"),
                    claimed_at=row.get("claimedAt"),
                    started_at=row.get("startedAt"),
                    finished_at=row.get("finishedAt"),
                    resume_from_stage=string_value(row.get("resumeFromStage", "")),
                    resume_from_clip_index=safe_int(row.get("resumeFromClipIndex"), 0),
                    failure_code=string_value(row.get("failureCode", "")),
                    failure_message=string_value(row.get("failureMessage", "")),
                    payload_json=write_json_object(safe_payload),
                    timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                    create_time=now_iso(),
                    update_time=now_iso(),
                    is_deleted=0,
                    remark="",
                )
            )

    async def _upsert_model_call(self, task_id: str, row: dict[str, Any]) -> None:
        model_call_id = string_value(row.get("modelCallId", row.get("id", "")))
        if not model_call_id:
            return
        result = await self.session.execute(
            select(BizTaskModelCall).where(BizTaskModelCall.task_model_call_id == model_call_id)
        )
        existing = result.scalars().first()
        now = now_iso()
        values = {
            "task_id": task_id,
            "call_kind": string_value(row.get("callKind", "")),
            "stage": string_value(row.get("stage", "")),
            "operation": string_value(row.get("operation", "")),
            "provider": string_value(row.get("provider", "")),
            "provider_model": string_value(row.get("providerModel", "")),
            "requested_model": string_value(row.get("requestedModel", "")),
            "resolved_model": string_value(row.get("resolvedModel", "")),
            "model_name": string_value(row.get("modelName", "")),
            "model_alias": string_value(row.get("modelAlias", "")),
            "endpoint_host": string_value(row.get("endpointHost", "")),
            "request_id": string_value(row.get("requestId", "")),
            "request_payload_json": write_json_object(ProviderPayloadSanitizer.sanitize(row.get("requestPayload", {}))),
            "response_payload_json": write_json_object(ProviderPayloadSanitizer.sanitize(row.get("responsePayload", {}))),
            "http_status": safe_int(row.get("httpStatus"), 0),
            "response_status_code": safe_int(row.get("responseStatusCode", row.get("responseCode")), 0),
            "success": 1 if bool(row.get("success")) else 0,
            "error_code": string_value(row.get("errorCode", "")),
            "error_message": string_value(row.get("errorMessage", "")),
            "latency_ms": safe_int(row.get("latencyMs"), 0),
            "duration_ms": safe_int(row.get("durationMs"), 0),
            "input_tokens": safe_int(row.get("inputTokens"), 0),
            "output_tokens": safe_int(row.get("outputTokens"), 0),
            "started_at": string_value(row.get("startedAt", now)),
            "finished_at": string_value(row.get("finishedAt", now)),
            "timezone_offset_minutes": safe_int(row.get("timezoneOffsetMinutes"), 0),
            "update_time": now,
            "is_deleted": 0,
            "remark": string_value(row.get("remark", "")),
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            return
        self.session.add(
            BizTaskModelCall(
                task_model_call_id=model_call_id,
                create_time=now,
                **values,
            )
        )

    async def _upsert_stage_run(self, task_id: str, row: dict[str, Any]) -> None:
        stage_run_id = string_value(row.get("stageRunId", row.get("id", "")))
        if not stage_run_id:
            return
        result = await self.session.execute(
            select(BizTaskStageRun).where(BizTaskStageRun.task_stage_run_id == stage_run_id)
        )
        existing = result.scalars().first()
        now = now_iso()
        values = {
            "task_id": task_id,
            "attempt_id": string_value(row.get("attemptId", "")),
            "stage_name": string_value(row.get("stageName", row.get("stage", ""))),
            "stage_seq": safe_int(row.get("stageSeq"), 0),
            "clip_index": safe_int(row.get("clipIndex"), 0),
            "status": _stage_run_status(row.get("status")),
            "worker_instance_id": string_value(row.get("workerInstanceId", "")),
            "started_at": string_value(row.get("startedAt", now)),
            "finished_at": string_value(row.get("finishedAt", "")) or None,
            "duration_ms": safe_int(row.get("durationMs"), 0),
            "input_summary_json": write_json_object(row.get("inputSummary", {})),
            "output_summary_json": write_json_object(row.get("outputSummary", {})),
            "error_code": string_value(row.get("errorCode", "")),
            "error_message": string_value(row.get("errorMessage", "")),
            "timezone_offset_minutes": safe_int(row.get("timezoneOffsetMinutes"), 0),
            "update_time": now,
            "is_deleted": 0,
            "remark": "",
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            return
        self.session.add(
            BizTaskStageRun(
                task_stage_run_id=stage_run_id,
                create_time=now,
                **values,
            )
        )

    async def _upsert_material_asset(
        self,
        task_id: str,
        task: TaskRecord | None,
        row: dict[str, Any],
    ) -> None:
        material_id = string_value(row.get("materialAssetId", row.get("materialId", row.get("id", ""))))
        if not material_id:
            return
        existing = await self._find_material_row(material_id)
        now = now_iso()
        metadata = object_value(ProviderPayloadSanitizer.sanitize(row.get("metadata", {})))
        owner_user_id = _optional_int(row.get("ownerUserId"))
        if owner_user_id is None and task is not None:
            owner_user_id = task.owner_user_id
        values = {
            "remark": string_value(row.get("remark", "")),
            "owner_user_id": owner_user_id or 0,
            "task_id": task_id,
            "workflow_id": string_value(row.get("workflowId", "")) or None,
            "source_task_id": string_value(row.get("sourceTaskId", "")) or None,
            "source_material_id": string_value(row.get("sourceMaterialId", "")) or None,
            "asset_role": string_value(row.get("assetRole", row.get("kind", ""))) or None,
            "stage_type": string_value(row.get("stageType", row.get("stage", ""))) or None,
            "clip_index": _optional_int(row.get("clipIndex")),
            "version_no": _optional_int(row.get("versionNo")),
            "selected_for_next": safe_int(row.get("selectedForNext"), 0),
            "user_rating": _optional_int(row.get("userRating")),
            "rating_note": string_value(row.get("ratingNote", "")) or None,
            "media_type": string_value(row.get("mediaType", "")) or None,
            "title": string_value(row.get("title", "")) or None,
            "origin_provider": string_value(row.get("originProvider", "")) or None,
            "origin_model": string_value(row.get("originModel", "")) or None,
            "remote_task_id": string_value(row.get("remoteTaskId", "")) or None,
            "remote_asset_id": string_value(row.get("remoteAssetId", "")) or None,
            "original_file_name": string_value(row.get("originalFileName", "")) or None,
            "stored_file_name": string_value(row.get("storedFileName", "")) or None,
            "file_ext": string_value(row.get("fileExt", "")) or None,
            "storage_provider": string_value(row.get("storageProvider", "")) or None,
            "mime_type": string_value(row.get("mimeType", "")) or None,
            "size_bytes": _optional_int(row.get("sizeBytes")),
            "sha256": string_value(row.get("sha256", "")) or None,
            "duration_seconds": _optional_float(row.get("durationSeconds")),
            "width": _optional_int(row.get("width")),
            "height": _optional_int(row.get("height")),
            "has_audio": 1 if bool(row.get("hasAudio")) else 0,
            "local_storage_path": string_value(row.get("storagePath", "")) or None,
            "local_file_path": string_value(row.get("localFilePath", row.get("storagePath", ""))) or None,
            "public_url": _material_public_url_from_payload(row) or None,
            "thumbnail_url": _material_thumbnail_url_from_payload(row) or None,
            "third_party_url": None,
            "remote_url": None,
            "metadata_json": write_json_object(metadata),
            "captured_at": string_value(row.get("capturedAt", row.get("createdAt", now))) or None,
            "timezone_offset_minutes": _optional_int(row.get("timezoneOffsetMinutes")),
            "update_time": now,
            "is_deleted": 0,
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            return
        self.session.add(
            BizMaterialAsset(
                material_asset_id=material_id,
                create_time=now,
                **values,
            )
        )

    async def _upsert_worker_instance(self, row: dict[str, Any]) -> None:
        worker_id = string_value(row.get("workerInstanceId", ""))
        if not worker_id:
            return
        existing = await self._find_worker_row(worker_id)
        now = now_iso()
        metadata = object_value(ProviderPayloadSanitizer.sanitize(row.get("metadata", {})))
        if existing:
            existing.worker_type = string_value(row.get("workerType", existing.worker_type))
            existing.queue_name = string_value(row.get("queueName", existing.queue_name))
            existing.host_name = string_value(row.get("hostName", existing.host_name))
            existing.process_id = safe_int(row.get("processId"), existing.process_id or 0)
            existing.status = string_value(row.get("status", existing.status))
            existing.last_heartbeat_at = string_value(row.get("lastHeartbeatAt", now))
            existing.stopped_at = string_value(row.get("stoppedAt", existing.stopped_at or ""))
            existing.metadata_json = write_json_object(metadata)
            existing.timezone_offset_minutes = safe_int(
                row.get("timezoneOffsetMinutes"), existing.timezone_offset_minutes or 0
            )
            existing.update_time = now
        else:
            self.session.add(
                BizWorkerInstance(
                    worker_instance_id=worker_id,
                    worker_type=string_value(row.get("workerType", "")),
                    queue_name=string_value(row.get("queueName", "default")),
                    host_name=string_value(row.get("hostName", "")),
                    process_id=safe_int(row.get("processId"), 0),
                    status=string_value(row.get("status", "")),
                    started_at=string_value(row.get("startedAt", now)),
                    last_heartbeat_at=string_value(row.get("lastHeartbeatAt", now)),
                    stopped_at=string_value(row.get("stoppedAt", "")),
                    metadata_json=write_json_object(metadata),
                    timezone_offset_minutes=safe_int(row.get("timezoneOffsetMinutes"), 0),
                    create_time=now,
                    update_time=now,
                    is_deleted=0,
                    remark="",
                )
            )
