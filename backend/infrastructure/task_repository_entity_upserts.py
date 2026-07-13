"""Entity upsert operations used by the atomic task mutation service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from backend.domain.json_payloads import object_value, write_json_object
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository_mapping import (
    _light_url,
    _material_public_url_from_payload,
    _material_thumbnail_url_from_payload,
    _optional_float,
    _optional_int,
    _stage_run_status,
)
from backend.models.task import (
    BizMaterialAsset,
    BizTaskAttempt,
    BizTaskModelCall,
    BizTaskResult,
    BizTaskStageRun,
    BizWorkerInstance,
)
from backend.services.provider_payload_sanitizer import ProviderPayloadSanitizer
from backend.shared import now_iso, safe_int, string_value


class TaskRepositoryEntityUpserts:
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
            "response_payload_json": write_json_object(
                ProviderPayloadSanitizer.sanitize(row.get("responsePayload", {}))
            ),
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

    async def _upsert_task_result(self, task_id: str, row: dict[str, Any]) -> None:
        result_id = string_value(row.get("resultId", row.get("id", "")))
        if not result_id:
            return
        result = await self.session.execute(select(BizTaskResult).where(BizTaskResult.task_result_id == result_id))
        existing = result.scalars().first()
        now = now_iso()
        values = {
            "task_id": task_id,
            "result_type": string_value(row.get("resultType", "")),
            "clip_index": safe_int(row.get("clipIndex"), 0),
            "title": string_value(row.get("title", "")),
            "reason": string_value(row.get("reason", "")),
            "source_model_call_id": string_value(row.get("sourceModelCallId", "")),
            "material_asset_id": string_value(row.get("materialAssetId", "")),
            "start_seconds": float(row.get("startSeconds") or 0),
            "end_seconds": float(row.get("endSeconds") or 0),
            "duration_seconds": float(row.get("durationSeconds") or 0),
            "preview_path": _light_url(row.get("previewPath", row.get("previewUrl", "")), 512),
            "download_path": _light_url(row.get("downloadPath", row.get("downloadUrl", "")), 512),
            "width": safe_int(row.get("width"), 0),
            "height": safe_int(row.get("height"), 0),
            "mime_type": string_value(row.get("mimeType", "")),
            "size_bytes": safe_int(row.get("sizeBytes"), 0),
            "remote_url": _light_url(row.get("remoteUrl", ""), 1024),
            "extra_json": write_json_object(row.get("extra", {})),
            "produced_at": string_value(row.get("producedAt", now)),
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
            BizTaskResult(
                task_result_id=result_id,
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
