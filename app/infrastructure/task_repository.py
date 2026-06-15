from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.domain.task_record import TaskRecord
from app.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from app.models.task import (
    BizTask,
    BizTaskAttempt,
    BizTaskModelCall,
    BizTaskQueueEvent,
    BizTaskResult,
    BizTaskStageRun,
    BizTaskStatusHistory,
    BizWorkerInstance,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _int_value(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


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
        aspect_ratio=record.aspect_ratio,
        min_duration_seconds=record.min_duration_seconds,
        max_duration_seconds=record.max_duration_seconds,
        output_count=None,
        source_primary_asset_id=None,
        source_file_name=record.source_file_name,
        source_asset_ids_json=None,
        source_file_names_json=None,
        request_payload_json=json.dumps(record.request_snapshot, ensure_ascii=False)
        if record.request_snapshot
        else None,
        context_json=json.dumps(record.execution_context, ensure_ascii=False)
        if record.execution_context
        else None,
        intro_template=record.intro_template,
        outro_template=record.outro_template,
        creative_prompt=record.creative_prompt,
        task_seed=record.task_seed,
        effect_rating=record.effect_rating,
        effect_rating_note=record.effect_rating_note,
        rated_at=record.rated_at,
        model_provider=None,
        execution_mode=None,
        editing_mode=record.editing_mode,
        status=record.status or "",
        progress=record.progress,
        error_code=None,
        error_message=record.error_message,
        plan_json=None,
        retry_count=record.retry_count,
        timezone_offset_minutes=None,
        started_at=record.started_at,
        finished_at=record.finished_at,
        create_time=record.created_at,
        update_time=record.updated_at,
        is_deleted=0,
    )


def _record_from_biz_task(row: BizTask) -> TaskRecord:
    """Convert a BizTask ORM row into a TaskRecord."""
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
        completed_output_count=0,
        current_attempt_no=0,
        has_transcript=False,
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
        transcript_text="",
        storyboard_script="",
        status=row.status or "",
        progress=row.progress or 0,
        created_at=row.create_time or "",
        updated_at=row.update_time or "",
        source_file_name=row.source_file_name or "",
        execution_context={},
        request_snapshot={},
    )
    # Parse JSON fields
    if row.context_json:
        try:
            rec.execution_context = json.loads(row.context_json)
        except (json.JSONDecodeError, TypeError):
            pass
    if row.request_payload_json:
        try:
            rec.request_snapshot = json.loads(row.request_payload_json)
        except (json.JSONDecodeError, TypeError):
            pass
    return rec


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class TaskRepository:
    """SQLAlchemy-based repository for TaskRecord aggregates.

    Mirrors the Java MybatisTaskRepository.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("No SQLAlchemy session available")
        return self._session

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def save(self, task_record: TaskRecord) -> None:
        """Upsert the main task row."""
        row = _biz_task_from_record(task_record)
        existing = await self.session.get(BizTask, task_record.id)
        if existing:
            # Update
            for col in BizTask.__table__.columns:
                col_name = col.name
                if hasattr(row, col_name) and col_name != "task_id":
                    setattr(existing, col_name, getattr(row, col_name))
        else:
            self.session.add(row)
        await self.session.flush()

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        """Persist a full mutation atomically (task + sub-entities)."""
        # 1. Task main row
        if mutation.task:
            await self.save(mutation.task)

        task_id = mutation.task_id or (mutation.task.id if mutation.task else "")

        # 2. Attempts (upsert by task_attempt_id)
        for row in mutation.attempts:
            await self._upsert_attempt(task_id, row)

        # 3. Status history
        for row in mutation.status_history_rows:
            self.session.add(BizTaskStatusHistory(
                task_status_history_id=_string_value(row.get("statusHistoryId", row.get("id", ""))),
                task_id=task_id,
                previous_status=_string_value(row.get("previousStatus", "")),
                current_status=_string_value(row.get("nextStatus", "")),
                progress=_int_value(row.get("progress")),
                stage=_string_value(row.get("stage")),
                event=_string_value(row.get("event")),
                message=_string_value(row.get("reason", row.get("message", ""))),
                payload_json=json.dumps(row.get("payload", {}), ensure_ascii=False),
                change_time=_string_value(row.get("changedAt", row.get("timestamp", _now_iso()))),
                operator_type="system",
                operator_id="",
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 4. Trace rows -> store as BizTaskStatusHistory with special event prefix
        for row in mutation.trace_rows:
            self.session.add(BizTaskStatusHistory(
                task_status_history_id=_string_value(row.get("traceId", row.get("id", ""))),
                task_id=task_id,
                previous_status="",
                current_status="",
                progress=0,
                stage=_string_value(row.get("stage")),
                event=_string_value(row.get("event")),
                message=_string_value(row.get("message")),
                payload_json=json.dumps(row.get("payload", {}), ensure_ascii=False),
                change_time=_string_value(row.get("timestamp", _now_iso())),
                operator_type="trace",
                operator_id="",
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 5. Stage runs
        for row in mutation.stage_run_rows:
            self.session.add(BizTaskStageRun(
                task_stage_run_id=_string_value(row.get("stageRunId", row.get("id", ""))),
                task_id=task_id,
                attempt_id=_string_value(row.get("attemptId", "")),
                stage_name=_string_value(row.get("stageName", row.get("stage", ""))),
                stage_seq=_int_value(row.get("stageSeq"), 0),
                clip_index=_int_value(row.get("clipIndex"), 0),
                status=_string_value(row.get("status", "")),
                worker_instance_id=_string_value(row.get("workerInstanceId", "")),
                started_at=_string_value(row.get("startedAt", "")),
                finished_at=_string_value(row.get("finishedAt", "")),
                duration_ms=_int_value(row.get("durationMs"), 0),
                input_summary_json=json.dumps(row.get("inputSummary", {}), ensure_ascii=False),
                output_summary_json=json.dumps(row.get("outputSummary", {}), ensure_ascii=False),
                error_code=_string_value(row.get("errorCode", "")),
                error_message=_string_value(row.get("errorMessage", "")),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 6. Model calls
        for row in mutation.model_call_rows:
            self.session.add(BizTaskModelCall(
                task_model_call_id=_string_value(row.get("modelCallId", row.get("id", ""))),
                task_id=task_id,
                call_kind=_string_value(row.get("callKind", "")),
                stage=_string_value(row.get("stage", "")),
                operation=_string_value(row.get("operation", "")),
                provider=_string_value(row.get("provider", "")),
                provider_model=_string_value(row.get("providerModel", "")),
                requested_model=_string_value(row.get("requestedModel", "")),
                resolved_model=_string_value(row.get("resolvedModel", "")),
                model_name=_string_value(row.get("modelName", "")),
                model_alias=_string_value(row.get("modelAlias", "")),
                endpoint_host=_string_value(row.get("endpointHost", "")),
                request_id=_string_value(row.get("requestId", "")),
                request_payload_json=json.dumps(row.get("requestPayload", {}), ensure_ascii=False),
                response_payload_json=json.dumps(row.get("responsePayload", {}), ensure_ascii=False),
                http_status=_int_value(row.get("httpStatus"), 0),
                response_status_code=_int_value(row.get("responseStatusCode"), 0),
                success=_int_value(row.get("success"), 0),
                error_code=_string_value(row.get("errorCode", "")),
                error_message=_string_value(row.get("errorMessage", "")),
                latency_ms=_int_value(row.get("latencyMs"), 0),
                duration_ms=_int_value(row.get("durationMs"), 0),
                input_tokens=_int_value(row.get("inputTokens"), 0),
                output_tokens=_int_value(row.get("outputTokens"), 0),
                started_at=_string_value(row.get("startedAt", "")),
                finished_at=_string_value(row.get("finishedAt", "")),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 7. Materials -> store as BizMaterialAsset (simplified)
        for row in mutation.material_rows:
            self.session.add(BizTaskModelCall(
                task_model_call_id="mat_" + _string_value(row.get("materialId", row.get("id", _now_iso()))),
                task_id=task_id,
                call_kind="material",
                stage=_string_value(row.get("stage", "")),
                operation="",
                provider="",
                provider_model="",
                requested_model="",
                resolved_model="",
                model_name=_string_value(row.get("mediaType", "")),
                model_alias="",
                endpoint_host="",
                request_id="",
                request_payload_json=json.dumps(row, ensure_ascii=False),
                response_payload_json="{}",
                http_status=0,
                response_status_code=0,
                success=1,
                error_code="",
                error_message="",
                latency_ms=0,
                duration_ms=0,
                input_tokens=0,
                output_tokens=0,
                started_at=_now_iso(),
                finished_at=_now_iso(),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 8. Results
        for row in mutation.result_rows:
            self.session.add(BizTaskResult(
                task_result_id=_string_value(row.get("resultId", row.get("id", ""))),
                task_id=task_id,
                result_type=_string_value(row.get("resultType", "")),
                clip_index=_int_value(row.get("clipIndex"), 0),
                title=_string_value(row.get("title", "")),
                reason=_string_value(row.get("reason", "")),
                source_model_call_id=_string_value(row.get("sourceModelCallId", "")),
                material_asset_id=_string_value(row.get("materialAssetId", "")),
                start_seconds=row.get("startSeconds"),
                end_seconds=row.get("endSeconds"),
                duration_seconds=row.get("durationSeconds"),
                preview_path=_string_value(row.get("previewPath", "")),
                download_path=_string_value(row.get("downloadPath", "")),
                width=_int_value(row.get("width"), 0),
                height=_int_value(row.get("height"), 0),
                mime_type=_string_value(row.get("mimeType", "")),
                size_bytes=_int_value(row.get("sizeBytes"), 0),
                remote_url=_string_value(row.get("remoteUrl", "")),
                extra_json=json.dumps(row.get("extra", {}), ensure_ascii=False),
                produced_at=_string_value(row.get("producedAt", _now_iso())),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 9. Queue events
        for row in mutation.queue_event_rows:
            self.session.add(BizTaskQueueEvent(
                task_queue_event_id=_string_value(row.get("taskQueueEventId", row.get("id", ""))),
                task_id=task_id,
                attempt_id=_string_value(row.get("attemptId", "")),
                queue_name=_string_value(row.get("queueName", "default")),
                event_type=_string_value(row.get("eventType", "")),
                worker_instance_id=_string_value(row.get("workerInstanceId", "")),
                queue_position_hint=_int_value(row.get("queuePositionHint"), 0),
                payload_json=json.dumps(row.get("payload", {}), ensure_ascii=False),
                event_time=_string_value(row.get("eventTime", _now_iso())),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

        # 10. Worker instances (upsert)
        for row in mutation.worker_instance_rows:
            await self._upsert_worker_instance(row)

        await self.session.flush()

    async def find_by_id(self, task_id: str) -> TaskRecord | None:
        """Load a task with all related sub-collections."""
        row = await self.session.get(BizTask, task_id)
        if row is None:
            return None
        rec = _record_from_biz_task(row)
        await self._load_sub_collections(rec)
        return rec

    async def find_all(self) -> list[TaskRecord]:
        """Load all non-deleted tasks."""
        stmt = select(BizTask).where(BizTask.is_deleted == 0).order_by(BizTask.create_time.desc())
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        records = [_record_from_biz_task(r) for r in rows]
        for rec in records:
            await self._load_sub_collections(rec)
        return records

    async def delete(self, task_id: str) -> None:
        """Soft delete a task."""
        stmt = update(BizTask).where(BizTask.task_id == task_id).values(is_deleted=1, update_time=_now_iso())
        await self.session.execute(stmt)
        await self.session.flush()

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
                "payload": json.loads(r.payload_json) if r.payload_json else {},
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
                "payload": json.loads(r.payload_json) if r.payload_json else {},
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
                "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
            }
            for r in rows
        ]

    async def find_worker_instance(self, worker_instance_id: str) -> dict[str, Any] | None:
        row = await self.session.get(BizWorkerInstance, worker_instance_id)
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
            "metadata": json.loads(row.metadata_json) if row.metadata_json else {},
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
            payload = {}
            if a.payload_json:
                try:
                    payload = json.loads(a.payload_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            rec.attempts.append({
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
            })
            if a.status in ("RUNNING", "QUEUED", "PENDING"):
                rec.active_attempt_id = a.task_attempt_id
                rec.current_attempt_no = a.attempt_no

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
            payload = {}
            if r.payload_json:
                try:
                    payload = json.loads(r.payload_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            rec.trace.append({
                "traceId": r.task_status_history_id,
                "timestamp": r.change_time or "",
                "level": "",
                "stage": r.stage or "",
                "event": r.event or "",
                "message": r.message or "",
                "payload": payload,
            })

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
            payload = {}
            if r.payload_json:
                try:
                    payload = json.loads(r.payload_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            rec.status_history.append({
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
            })

        # Load model calls (and materials stored as model calls)
        stmt = (
            select(BizTaskModelCall)
            .where(BizTaskModelCall.task_id == tid, BizTaskModelCall.is_deleted == 0)
            .order_by(BizTaskModelCall.create_time.asc())
        )
        result = await self.session.execute(stmt)
        for m in result.scalars().all():
            if m.call_kind == "material":
                req_payload = {}
                if m.request_payload_json:
                    try:
                        req_payload = json.loads(m.request_payload_json)
                    except (json.JSONDecodeError, TypeError):
                        pass
                rec.materials.append(req_payload)
            else:
                req_payload = {}
                if m.request_payload_json:
                    try:
                        req_payload = json.loads(m.request_payload_json)
                    except (json.JSONDecodeError, TypeError):
                        pass
                resp_payload = {}
                if m.response_payload_json:
                    try:
                        resp_payload = json.loads(m.response_payload_json)
                    except (json.JSONDecodeError, TypeError):
                        pass
                rec.model_calls.append({
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
                })

        # Load results
        stmt = (
            select(BizTaskResult)
            .where(BizTaskResult.task_id == tid, BizTaskResult.is_deleted == 0)
            .order_by(BizTaskResult.produced_at.asc())
        )
        result = await self.session.execute(stmt)
        for r in result.scalars().all():
            extra = {}
            if r.extra_json:
                try:
                    extra = json.loads(r.extra_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            rec.outputs.append({
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
            })

    async def _upsert_attempt(self, task_id: str, row: dict[str, Any]) -> None:
        attempt_id = _string_value(row.get("attemptId", ""))
        if not attempt_id:
            return
        existing = await self.session.get(BizTaskAttempt, attempt_id)
        safe_payload = row.get("payload", {})
        if existing:
            existing.status = _string_value(row.get("status", existing.status))
            existing.trigger_type = _string_value(row.get("triggerType", existing.trigger_type))
            existing.queue_name = _string_value(row.get("queueName", existing.queue_name))
            existing.worker_instance_id = _string_value(row.get("workerInstanceId", existing.worker_instance_id))
            existing.queue_entered_at = row.get("queueEnteredAt", existing.queue_entered_at)
            existing.queue_left_at = row.get("queueLeftAt", existing.queue_left_at)
            existing.claimed_at = row.get("claimedAt", existing.claimed_at)
            existing.started_at = row.get("startedAt", existing.started_at)
            existing.finished_at = row.get("finishedAt", existing.finished_at)
            existing.resume_from_stage = _string_value(row.get("resumeFromStage", existing.resume_from_stage))
            existing.resume_from_clip_index = _int_value(row.get("resumeFromClipIndex"), existing.resume_from_clip_index or 0)
            existing.failure_code = _string_value(row.get("failureCode", existing.failure_code))
            existing.failure_message = _string_value(row.get("failureMessage", existing.failure_message))
            existing.payload_json = json.dumps(safe_payload, ensure_ascii=False)
            existing.update_time = _now_iso()
        else:
            self.session.add(BizTaskAttempt(
                task_attempt_id=attempt_id,
                task_id=task_id,
                attempt_no=_int_value(row.get("attemptNo"), 0),
                trigger_type=_string_value(row.get("triggerType", "")),
                status=_string_value(row.get("status", "")),
                queue_name=_string_value(row.get("queueName", "default")),
                worker_instance_id=_string_value(row.get("workerInstanceId", "")),
                queue_entered_at=row.get("queueEnteredAt"),
                queue_left_at=row.get("queueLeftAt"),
                claimed_at=row.get("claimedAt"),
                started_at=row.get("startedAt"),
                finished_at=row.get("finishedAt"),
                resume_from_stage=_string_value(row.get("resumeFromStage", "")),
                resume_from_clip_index=_int_value(row.get("resumeFromClipIndex"), 0),
                failure_code=_string_value(row.get("failureCode", "")),
                failure_message=_string_value(row.get("failureMessage", "")),
                payload_json=json.dumps(safe_payload, ensure_ascii=False),
                timezone_offset_minutes=None,
                create_time=_now_iso(),
                update_time=_now_iso(),
                is_deleted=0,
            ))

    async def _upsert_worker_instance(self, row: dict[str, Any]) -> None:
        worker_id = _string_value(row.get("workerInstanceId", ""))
        if not worker_id:
            return
        existing = await self.session.get(BizWorkerInstance, worker_id)
        now = _now_iso()
        metadata = row.get("metadata", {})
        if existing:
            existing.worker_type = _string_value(row.get("workerType", existing.worker_type))
            existing.queue_name = _string_value(row.get("queueName", existing.queue_name))
            existing.host_name = _string_value(row.get("hostName", existing.host_name))
            existing.process_id = _int_value(row.get("processId"), existing.process_id or 0)
            existing.status = _string_value(row.get("status", existing.status))
            existing.last_heartbeat_at = _string_value(row.get("lastHeartbeatAt", now))
            existing.stopped_at = _string_value(row.get("stoppedAt", existing.stopped_at or ""))
            existing.metadata_json = json.dumps(metadata, ensure_ascii=False)
            existing.update_time = now
        else:
            self.session.add(BizWorkerInstance(
                worker_instance_id=worker_id,
                worker_type=_string_value(row.get("workerType", "")),
                queue_name=_string_value(row.get("queueName", "default")),
                host_name=_string_value(row.get("hostName", "")),
                process_id=_int_value(row.get("processId"), 0),
                status=_string_value(row.get("status", "")),
                started_at=_string_value(row.get("startedAt", now)),
                last_heartbeat_at=_string_value(row.get("lastHeartbeatAt", now)),
                stopped_at=_string_value(row.get("stoppedAt", "")),
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                timezone_offset_minutes=None,
                create_time=now,
                update_time=now,
                is_deleted=0,
            ))
