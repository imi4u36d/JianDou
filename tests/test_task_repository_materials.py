from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from sqlalchemy import select

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.models.task import (
    BizMaterialAsset,
    BizTask,
    BizTaskModelCall,
    BizTaskQueueEvent,
    BizTaskStatusHistory,
    BizWorkerInstance,
)


async def test_repository_persists_material_rows_as_material_assets(db_session) -> None:
    task = TaskRecord(
        id="task_material_repository",
        owner_user_id=7,
        task_type="video_generation",
        title="Material repository",
        status="PENDING",
        progress=0,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    material = {
        "id": "asset_material_repository",
        "ownerUserId": 7,
        "kind": "clip",
        "mediaType": "video",
        "title": "Clip asset",
        "originProvider": "provider",
        "originModel": "model",
        "remoteTaskId": "remote_task",
        "originalFileName": "clip1.mp4",
        "storedFileName": "clip1.mp4",
        "fileExt": "mp4",
        "storageProvider": "local",
        "mimeType": "video/mp4",
        "sizeBytes": 1024,
        "durationSeconds": 5.5,
        "width": 1280,
        "height": 720,
        "hasAudio": True,
        "storagePath": "/tmp/clip1.mp4",
        "localFilePath": "/tmp/clip1.mp4",
        "fileUrl": "/storage/clip1.mp4",
        "previewUrl": "/storage/clip1-thumb.jpg",
        "thumbnailUrl": "/storage/clip1-thumb.jpg",
        "remoteUrl": "https://provider.example.test/clip1.mp4",
        "metadata": {"clipIndex": 1, "taskArtifact": True},
        "createdAt": "2026-01-01T00:01:00+00:00",
        "clipIndex": 1,
    }
    repository = TaskRepository(db_session)
    mutation = TaskPersistenceMutation().set_task(task).add_material(material)

    await repository.save_mutation(mutation)

    asset_result = await db_session.execute(
        select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == "asset_material_repository")
    )
    asset = asset_result.scalar_one()
    assert asset.task_id == task.id
    assert asset.owner_user_id == 7
    assert asset.asset_role == "clip"
    assert asset.media_type == "video"
    assert asset.public_url == "/storage/clip1.mp4"
    assert asset.thumbnail_url == "/storage/clip1-thumb.jpg"
    assert asset.local_storage_path == "/tmp/clip1.mp4"
    assert asset.has_audio == 1

    model_call_result = await db_session.execute(
        select(BizTaskModelCall).where(
            BizTaskModelCall.task_id == task.id,
            BizTaskModelCall.call_kind == "material",
        )
    )
    assert model_call_result.scalars().all() == []

    loaded = await repository.find_by_id(task.id)
    assert loaded is not None
    assert loaded.materials == [
        {
            "id": "asset_material_repository",
            "materialAssetId": "asset_material_repository",
            "ownerUserId": 7,
            "taskId": task.id,
            "workflowId": "",
            "sourceTaskId": "",
            "sourceMaterialId": "",
            "kind": "clip",
            "assetRole": "clip",
            "stageType": "",
            "clipIndex": 1,
            "versionNo": None,
            "selectedForNext": 0,
            "userRating": None,
            "ratingNote": "",
            "mediaType": "video",
            "title": "Clip asset",
            "originProvider": "provider",
            "originModel": "model",
            "remoteTaskId": "remote_task",
            "remoteAssetId": "",
            "originalFileName": "clip1.mp4",
            "storedFileName": "clip1.mp4",
            "fileExt": "mp4",
            "storageProvider": "local",
            "mimeType": "video/mp4",
            "sizeBytes": 1024,
            "sha256": "",
            "durationSeconds": 5.5,
            "width": 1280,
            "height": 720,
            "hasAudio": True,
            "storagePath": "/tmp/clip1.mp4",
            "localFilePath": "/tmp/clip1.mp4",
            "fileUrl": "/storage/clip1.mp4",
            "previewUrl": "/storage/clip1-thumb.jpg",
            "thumbnailUrl": "/storage/clip1-thumb.jpg",
            "thirdPartyUrl": "",
            "remoteUrl": "https://provider.example.test/clip1.mp4",
            "metadata": {"clipIndex": 1, "taskArtifact": True},
            "createdAt": "2026-01-01T00:01:00+00:00",
        }
    ]


async def test_repository_reads_malformed_json_columns_as_empty_payloads(db_session) -> None:
    db_session.add(
        BizTask(
            task_id="task_bad_json_repository",
            owner_user_id=7,
            task_type="video_generation",
            title="Bad JSON repository",
            description=None,
            aspect_ratio="16:9",
            min_duration_seconds=5,
            max_duration_seconds=12,
            output_count=0,
            source_primary_asset_id="",
            source_file_name="",
            source_asset_ids_json=None,
            source_file_names_json=None,
            request_payload_json="{bad",
            context_json="[1, 2]",
            intro_template="",
            outro_template="",
            creative_prompt="",
            task_seed=None,
            effect_rating=None,
            effect_rating_note="",
            rated_at=None,
            model_provider="",
            execution_mode="",
            editing_mode="",
            status="PENDING",
            progress=0,
            error_code="",
            error_message=None,
            plan_json=None,
            retry_count=0,
            timezone_offset_minutes=0,
            started_at=None,
            finished_at=None,
            create_time="2026-01-01T00:00:00+00:00",
            update_time="2026-01-01T00:00:00+00:00",
            is_deleted=0,
            remark="",
        )
    )
    db_session.add(
        BizTaskStatusHistory(
            task_status_history_id="trace_bad_json_repository",
            task_id="task_bad_json_repository",
            previous_status="",
            current_status="",
            progress=0,
            stage="render",
            event="trace",
            message="bad trace payload",
            payload_json="{bad",
            change_time="2026-01-01T00:00:01+00:00",
            operator_type="trace",
            operator_id="",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:01+00:00",
            update_time="2026-01-01T00:00:01+00:00",
            is_deleted=0,
            remark="",
        )
    )
    db_session.add(
        BizTaskQueueEvent(
            task_queue_event_id="queue_bad_json_repository",
            task_id="task_bad_json_repository",
            attempt_id="",
            queue_name="default",
            event_type="enqueued",
            worker_instance_id="",
            queue_position_hint=0,
            payload_json="[1, 2]",
            event_time="2026-01-01T00:00:02+00:00",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:02+00:00",
            update_time="2026-01-01T00:00:02+00:00",
            is_deleted=0,
            remark="",
        )
    )
    db_session.add(
        BizWorkerInstance(
            worker_instance_id="worker_bad_json_repository",
            worker_type="render",
            queue_name="default",
            host_name="host",
            process_id=123,
            status="RUNNING",
            started_at="2026-01-01T00:00:03+00:00",
            last_heartbeat_at="2026-01-01T00:00:04+00:00",
            stopped_at="",
            metadata_json="{bad",
            timezone_offset_minutes=0,
            create_time="2026-01-01T00:00:03+00:00",
            update_time="2026-01-01T00:00:03+00:00",
            is_deleted=0,
            remark="",
        )
    )
    await db_session.commit()

    repository = TaskRepository(db_session)
    loaded = await repository.find_by_id("task_bad_json_repository")
    traces = await repository.list_traces("task_bad_json_repository", stage=None, level=None, q=None, limit=10)
    queue_events = await repository.list_queue_events("task_bad_json_repository", limit=10)
    worker = await repository.find_worker_instance("worker_bad_json_repository")

    assert loaded is not None
    assert loaded.request_snapshot == {}
    assert loaded.execution_context == {}
    assert loaded.trace[0]["payload"] == {}
    assert traces[0]["payload"] == {}
    assert queue_events[0]["payload"] == {}
    assert worker is not None
    assert worker["metadata"] == {}
