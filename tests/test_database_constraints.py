"""Database constraint tests for backend schema contracts."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.models.log import BizRequestLog
from backend.models.public_share import BizPublicShare, BizPublicShareLike
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
from backend.models.workflow import BizStageVersion, BizStageWorkflow

_CONSTRAINT_ERROR = (IntegrityError, OperationalError)


def _task_row(**overrides):
    row = {
        "task_id": "task_constraints",
        "owner_user_id": 1,
        "task_type": "video_generation",
        "title": "Constraint task",
        "description": None,
        "aspect_ratio": "16:9",
        "min_duration_seconds": 5,
        "max_duration_seconds": 12,
        "output_count": None,
        "source_primary_asset_id": None,
        "source_file_name": "",
        "source_asset_ids_json": None,
        "source_file_names_json": None,
        "request_payload_json": "{}",
        "context_json": "{}",
        "intro_template": "",
        "outro_template": "",
        "creative_prompt": "",
        "task_seed": None,
        "effect_rating": None,
        "effect_rating_note": "",
        "rated_at": None,
        "model_provider": "",
        "execution_mode": "",
        "editing_mode": "",
        "status": "PENDING",
        "progress": 0,
        "error_code": "",
        "error_message": None,
        "plan_json": None,
        "retry_count": 0,
        "timezone_offset_minutes": 0,
        "started_at": None,
        "finished_at": None,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizTask(**row)


def _model_call_row(**overrides):
    row = {
        "task_model_call_id": "model_call_constraints",
        "task_id": "task_1",
        "call_kind": "video",
        "stage": "render",
        "operation": "generate",
        "provider": "provider",
        "provider_model": "provider-model",
        "requested_model": "requested-model",
        "resolved_model": "resolved-model",
        "model_name": "",
        "model_alias": "",
        "endpoint_host": "api.example.com",
        "request_id": "req_1",
        "request_payload_json": "{}",
        "response_payload_json": "{}",
        "http_status": 200,
        "response_status_code": 0,
        "success": 1,
        "error_code": "",
        "error_message": None,
        "latency_ms": 10,
        "duration_ms": 20,
        "input_tokens": 1,
        "output_tokens": 2,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizTaskModelCall(**row)


def _result_row(**overrides):
    row = {
        "task_result_id": "result_constraints",
        "task_id": "task_1",
        "result_type": "video",
        "clip_index": 0,
        "title": "Clip",
        "reason": "",
        "source_model_call_id": "model_call_1",
        "material_asset_id": "asset_1",
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "duration_seconds": 1.0,
        "preview_path": "/preview.mp4",
        "download_path": "/download.mp4",
        "width": 1280,
        "height": 720,
        "mime_type": "video/mp4",
        "size_bytes": 100,
        "remote_url": "",
        "extra_json": "{}",
        "produced_at": "2026-01-01T00:00:00+00:00",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizTaskResult(**row)


def _status_history_row(**overrides):
    row = {
        "task_status_history_id": "history_constraints",
        "task_id": "task_1",
        "previous_status": "",
        "current_status": "",
        "progress": 0,
        "stage": "trace",
        "event": "heartbeat",
        "message": "",
        "payload_json": "{}",
        "change_time": "2026-01-01T00:00:00+00:00",
        "operator_type": "system",
        "operator_id": "",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizTaskStatusHistory(**row)


def _material_asset_row(**overrides):
    row = {
        "material_asset_id": "asset_constraints",
        "remark": "",
        "owner_user_id": 1,
        "task_id": "task_1",
        "workflow_id": "wf_1",
        "source_task_id": None,
        "source_material_id": None,
        "asset_role": "source",
        "stage_type": "keyframe",
        "clip_index": 0,
        "version_no": 1,
        "selected_for_next": 0,
        "user_rating": None,
        "rating_note": None,
        "media_type": "image",
        "title": "Asset",
        "origin_provider": "",
        "origin_model": "",
        "remote_task_id": "",
        "remote_asset_id": "",
        "original_file_name": "asset.png",
        "stored_file_name": "asset.png",
        "file_ext": "png",
        "storage_provider": "local",
        "mime_type": "image/png",
        "size_bytes": 100,
        "sha256": None,
        "duration_seconds": None,
        "width": 512,
        "height": 512,
        "has_audio": 0,
        "local_storage_path": "/tmp/asset.png",
        "local_file_path": None,
        "public_url": "/assets/asset.png",
        "thumbnail_url": None,
        "third_party_url": None,
        "remote_url": None,
        "metadata_json": "{}",
        "captured_at": "2026-01-01T00:00:00+00:00",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
    }
    row.update(overrides)
    return BizMaterialAsset(**row)


def _public_share_row(**overrides):
    row = {
        "share_id": "share_constraints",
        "owner_user_id": 1,
        "material_asset_id": "asset_constraints",
        "source_type": "material",
        "source_id": "asset_constraints",
        "media_type": "image",
        "title": "Share",
        "status": "ACTIVE",
        "like_count": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizPublicShare(**row)


def _public_share_like_row(**overrides):
    row = {
        "like_id": "like_constraints",
        "share_id": "share_constraints",
        "user_id": 1,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
        "remark": "",
    }
    row.update(overrides)
    return BizPublicShareLike(**row)


def _request_log_row(**overrides):
    row = {
        "request_log_id": "request_log_constraints",
        "owner_user_id": 1,
        "owner_ref_id": "task_1",
        "task_id": "task_1",
        "workflow_id": None,
        "request_type": "video",
        "stage": "render",
        "operation": "generate",
        "provider": "provider",
        "provider_model": "provider-model",
        "requested_model": "requested-model",
        "resolved_model": "resolved-model",
        "endpoint_host": "api.example.com",
        "request_id": "req_1",
        "status": "COMPLETED",
        "success": 1,
        "http_status": 200,
        "error_code": "",
        "error_message": None,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "duration_ms": 1000,
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00+00:00",
        "update_time": "2026-01-01T00:00:00+00:00",
        "is_deleted": 0,
    }
    row.update(overrides)
    return BizRequestLog(**row)


async def test_task_rejects_unknown_status(db_session):
    db_session.add(_task_row(status="MYSTERY"))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_rejects_progress_out_of_range(db_session):
    db_session.add(_task_row(task_id="task_bad_progress", progress=101))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_rejects_invalid_duration_range(db_session):
    db_session.add(_task_row(task_id="task_bad_duration", min_duration_seconds=12, max_duration_seconds=5))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_workflow_rejects_unknown_status(db_session):
    db_session.add(
        BizStageWorkflow(
            workflow_id="wf_invalid_status",
            owner_user_id=1,
            title="Invalid workflow",
            aspect_ratio="16:9",
            text_analysis_model="text-model",
            image_model="image-model",
            video_model="video-model",
            video_size="1280*720",
            min_duration_seconds=5,
            max_duration_seconds=12,
            duration_mode="auto",
            status="MYSTERY",
            current_stage="storyboard",
            selected_storyboard_version_id="",
            final_join_asset_id="",
            effect_rating=None,
            effect_rating_note="",
            metadata_json="{}",
            timezone_offset_minutes=0,
            is_deleted=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_stage_version_rejects_out_of_range_rating(db_session):
    db_session.add(
        BizStageVersion(
            stage_version_id="sv_invalid_rating",
            workflow_id="wf_1",
            owner_user_id=1,
            stage_type="storyboard",
            clip_index=0,
            version_no=1,
            title="Storyboard",
            status="COMPLETED",
            selected=0,
            rating=6,
            rating_note="",
            parent_version_id="",
            source_material_asset_id="",
            material_asset_id="",
            preview_url="",
            download_url="",
            input_summary_json="{}",
            output_summary_json="{}",
            model_call_summary_json="{}",
            timezone_offset_minutes=0,
            is_deleted=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_attempt_rejects_unknown_status(db_session):
    db_session.add(
        BizTaskAttempt(
            task_attempt_id="attempt_invalid_status",
            task_id="task_1",
            attempt_no=1,
            trigger_type="create",
            status="MAYBE",
            queue_name="default",
            worker_instance_id="",
            resume_from_stage="",
            resume_from_clip_index=0,
            failure_code="",
            failure_message=None,
            payload_json="{}",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            is_deleted=0,
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_stage_run_rejects_unknown_status(db_session):
    db_session.add(
        BizTaskStageRun(
            task_stage_run_id="stage_run_invalid_status",
            task_id="task_1",
            attempt_id="attempt_1",
            stage_name="render",
            stage_seq=1,
            clip_index=0,
            status="success",
            worker_instance_id="worker_1",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:00+00:00",
            duration_ms=1,
            input_summary_json="{}",
            output_summary_json="{}",
            error_code="",
            error_message=None,
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            is_deleted=0,
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_repository_normalizes_legacy_stage_run_status(db_session):
    repository = TaskRepository(db_session)
    mutation = TaskPersistenceMutation(task_id="task_legacy_stage_status").add_stage_run(
        {
            "stageRunId": "stage_run_legacy_success",
            "attemptId": "attempt_1",
            "stageName": "render",
            "stageSeq": 1,
            "clipIndex": 0,
            "status": "success",
            "workerInstanceId": "worker_1",
            "startedAt": "2026-01-01T00:00:00+00:00",
            "finishedAt": "2026-01-01T00:00:01+00:00",
            "durationMs": 1000,
            "inputSummary": {},
            "outputSummary": {},
        }
    )

    await repository.save_mutation(mutation)

    result = await db_session.execute(
        select(BizTaskStageRun).where(BizTaskStageRun.task_stage_run_id == "stage_run_legacy_success")
    )
    row = result.scalar_one()
    assert row.status == "COMPLETED"


async def test_task_status_history_rejects_progress_out_of_range(db_session):
    db_session.add(_status_history_row(progress=101))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_model_call_rejects_invalid_success_flag(db_session):
    db_session.add(_model_call_row(success=2))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_model_call_rejects_negative_token_count(db_session):
    db_session.add(_model_call_row(task_model_call_id="model_call_bad_tokens", input_tokens=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_request_log_rejects_blank_request_type(db_session):
    db_session.add(_request_log_row(request_type="   "))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_request_log_rejects_invalid_success_flag(db_session):
    db_session.add(_request_log_row(request_log_id="request_log_bad_success", success=2))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_request_log_rejects_negative_duration_and_http_status(db_session):
    db_session.add(_request_log_row(request_log_id="request_log_bad_duration", duration_ms=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()

    await db_session.rollback()
    db_session.add(_request_log_row(request_log_id="request_log_bad_http", http_status=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_request_log_rejects_invalid_soft_delete_flag(db_session):
    db_session.add(_request_log_row(request_log_id="request_log_bad_delete", is_deleted=2))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_result_rejects_negative_media_dimensions(db_session):
    db_session.add(_result_row(width=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_task_result_rejects_negative_duration(db_session):
    db_session.add(_result_row(task_result_id="result_bad_duration", duration_seconds=-0.1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_queue_event_rejects_unknown_event_type(db_session):
    db_session.add(
        BizTaskQueueEvent(
            task_queue_event_id="queue_event_invalid_type",
            task_id="task_1",
            attempt_id="attempt_1",
            queue_name="default",
            event_type="teleported",
            worker_instance_id="worker_1",
            queue_position_hint=0,
            payload_json="{}",
            event_time="2026-01-01T00:00:00+00:00",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            is_deleted=0,
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_worker_instance_rejects_unknown_status(db_session):
    db_session.add(
        BizWorkerInstance(
            worker_instance_id="worker_invalid_status",
            worker_type="default",
            queue_name="default",
            host_name="localhost",
            process_id=1,
            status="IDLE",
            started_at="2026-01-01T00:00:00+00:00",
            last_heartbeat_at="2026-01-01T00:00:00+00:00",
            stopped_at=None,
            metadata_json="{}",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            is_deleted=0,
            remark="",
        )
    )

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_material_asset_rejects_out_of_range_rating(db_session):
    db_session.add(_material_asset_row(user_rating=6))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_material_asset_rejects_invalid_selected_flag(db_session):
    db_session.add(_material_asset_row(material_asset_id="asset_bad_selected", selected_for_next=2))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_material_asset_rejects_negative_size(db_session):
    db_session.add(_material_asset_row(material_asset_id="asset_bad_size", size_bytes=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_public_share_rejects_invalid_status(db_session):
    db_session.add(_public_share_row(status="PUBLISHED"))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_public_share_rejects_negative_like_count(db_session):
    db_session.add(_public_share_row(share_id="share_bad_like_count", material_asset_id="asset_bad_like_count", like_count=-1))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_public_share_like_rejects_duplicate_share_user(db_session):
    db_session.add_all([
        _public_share_like_row(like_id="like_constraints_1"),
        _public_share_like_row(like_id="like_constraints_2"),
    ])

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()


async def test_public_share_like_rejects_invalid_deleted_flag(db_session):
    db_session.add(_public_share_like_row(like_id="like_bad_deleted", is_deleted=2))

    with pytest.raises(_CONSTRAINT_ERROR):
        await db_session.commit()
