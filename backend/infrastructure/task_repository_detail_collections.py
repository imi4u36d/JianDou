"""Child-row read models used by lightweight task detail responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.json_payloads import read_json_object
from backend.models.task import (
    BizTaskAttempt,
    BizTaskModelCall,
    BizTaskStageRun,
    BizTaskStatusHistory,
)

if TYPE_CHECKING:
    from backend.infrastructure.task_repository_detail_queries import TaskRepositoryDetailQueryService


class TaskRepositoryDetailCollectionQueryService:
    """Load attempts, status history, stage runs, and lightweight model calls."""

    def __init__(self, detail_service: TaskRepositoryDetailQueryService) -> None:
        self._detail_service = detail_service

    def __getattr__(self, name: str) -> Any:
        return getattr(self._detail_service, name)

    async def attempt_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
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

    async def active_attempt_row(self, session: AsyncSession, task_id: str) -> dict[str, Any]:
        stmt = (
            select(
                BizTaskAttempt.task_attempt_id,
                BizTaskAttempt.task_id,
                BizTaskAttempt.attempt_no,
                BizTaskAttempt.trigger_type,
                BizTaskAttempt.status,
                BizTaskAttempt.queue_name,
                BizTaskAttempt.worker_instance_id,
                BizTaskAttempt.queue_entered_at,
                BizTaskAttempt.queue_left_at,
                BizTaskAttempt.claimed_at,
                BizTaskAttempt.started_at,
                BizTaskAttempt.finished_at,
                BizTaskAttempt.resume_from_stage,
                BizTaskAttempt.resume_from_clip_index,
                BizTaskAttempt.failure_code,
                BizTaskAttempt.failure_message,
            )
            .where(
                BizTaskAttempt.task_id == task_id,
                BizTaskAttempt.status.in_(("RUNNING", "QUEUED", "PENDING")),
                BizTaskAttempt.is_deleted == 0,
            )
            .order_by(BizTaskAttempt.attempt_no.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            return {}
        return {
            "attemptId": row.task_attempt_id,
            "taskId": row.task_id,
            "attemptNo": row.attempt_no,
            "triggerType": row.trigger_type or "",
            "status": row.status,
            "queueName": row.queue_name or "",
            "workerInstanceId": row.worker_instance_id or "",
            "queueEnteredAt": row.queue_entered_at,
            "queueLeftAt": row.queue_left_at,
            "claimedAt": row.claimed_at,
            "startedAt": row.started_at,
            "finishedAt": row.finished_at,
            "resumeFromStage": row.resume_from_stage or "",
            "resumeFromClipIndex": row.resume_from_clip_index or 0,
            "failureCode": row.failure_code or "",
            "failureMessage": row.failure_message or "",
            "payload": {},
        }

    async def status_history_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
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

    async def stage_run_rows(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
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

    async def model_call_rows_light(self, session: AsyncSession, task_id: str) -> list[dict[str, Any]]:
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
