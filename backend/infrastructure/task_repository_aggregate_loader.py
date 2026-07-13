from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from backend.domain.json_payloads import read_json_object
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository_mapping import _material_from_row, _record_from_biz_task
from backend.models.task import (
    BizMaterialAsset,
    BizTaskAttempt,
    BizTaskModelCall,
    BizTaskResult,
    BizTaskStatusHistory,
)

if TYPE_CHECKING:
    from backend.infrastructure.task_repository import TaskRepository


class TaskRepositoryAggregateLoader:
    """Load the complete TaskRecord aggregate and its child collections."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    async def load_task_record_without_lock(self, task_id: str) -> TaskRecord | None:
        row = await self._find_task_row(task_id)
        if row is None:
            return None
        rec = _record_from_biz_task(row)
        await self._load_sub_collections(rec)
        return rec

    async def _load_sub_collections(self, rec: TaskRecord) -> None:
        """Load all sub-collections for a TaskRecord from DB."""
        tid = rec.id
        if not tid:
            return

        await self._load_attempts(rec, tid)
        await self._load_status_history(rec, tid)
        await self._load_model_calls(rec, tid)
        await self._load_materials(rec, tid)
        await self._load_results(rec, tid)

    async def _load_attempts(self, rec: TaskRecord, task_id: str) -> None:
        stmt = (
            select(BizTaskAttempt)
            .where(BizTaskAttempt.task_id == task_id, BizTaskAttempt.is_deleted == 0)
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

    async def _load_status_history(self, rec: TaskRecord, task_id: str) -> None:
        trace_stmt = (
            select(BizTaskStatusHistory)
            .where(
                BizTaskStatusHistory.task_id == task_id,
                BizTaskStatusHistory.operator_type == "trace",
                BizTaskStatusHistory.is_deleted == 0,
            )
            .order_by(BizTaskStatusHistory.change_time.asc())
        )
        trace_result = await self.session.execute(trace_stmt)
        for r in trace_result.scalars().all():
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
        history_stmt = (
            select(BizTaskStatusHistory)
            .where(
                BizTaskStatusHistory.task_id == task_id,
                BizTaskStatusHistory.operator_type != "trace",
                BizTaskStatusHistory.is_deleted == 0,
            )
            .order_by(BizTaskStatusHistory.change_time.asc())
        )
        history_result = await self.session.execute(history_stmt)
        for r in history_result.scalars().all():
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

    async def _load_model_calls(self, rec: TaskRecord, task_id: str) -> None:
        stmt = (
            select(BizTaskModelCall)
            .where(BizTaskModelCall.task_id == task_id, BizTaskModelCall.is_deleted == 0)
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

    async def _load_materials(self, rec: TaskRecord, task_id: str) -> None:
        stmt = (
            select(BizMaterialAsset)
            .where(BizMaterialAsset.task_id == task_id, BizMaterialAsset.is_deleted == 0)
            .order_by(BizMaterialAsset.create_time.asc())
        )
        result = await self.session.execute(stmt)
        for asset in result.scalars().all():
            rec.materials.append(_material_from_row(asset))

    async def _load_results(self, rec: TaskRecord, task_id: str) -> None:
        stmt = (
            select(BizTaskResult)
            .where(BizTaskResult.task_id == task_id, BizTaskResult.is_deleted == 0)
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
