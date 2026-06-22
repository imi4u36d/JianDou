from __future__ import annotations

import pytest
pytestmark = pytest.mark.service
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_view_mapper import WorkflowViewMapper


def _workflow() -> BizStageWorkflow:
    return BizStageWorkflow(
        workflow_id="wf_mapper",
        owner_user_id=1,
        title="Mapper Workflow",
        transcript_text="story",
        aspect_ratio="16:9",
        style_preset="cinematic",
        text_analysis_model="text",
        image_model="image",
        video_model="video",
        video_size="1280*720",
        duration_mode="auto",
        min_duration_seconds=5,
        max_duration_seconds=12,
        status="READY",
        current_stage="video",
        selected_storyboard_version_id="sv_story",
        final_join_asset_id="mat_final",
        effect_rating=None,
        effect_rating_note="",
        metadata_json="{}",
        timezone_offset_minutes=0,
        create_time="2026-01-01T00:00:00Z",
        update_time="2026-01-01T00:00:00Z",
        is_deleted=0,
        remark="",
    )


def _version(**overrides) -> BizStageVersion:
    values = {
        "stage_version_id": "sv_default",
        "workflow_id": "wf_mapper",
        "owner_user_id": 1,
        "stage_type": "storyboard",
        "clip_index": 0,
        "version_no": 1,
        "title": "Version",
        "status": "COMPLETED",
        "selected": 1,
        "rating": None,
        "rating_note": "",
        "rated_at": None,
        "parent_version_id": "",
        "source_material_asset_id": "",
        "material_asset_id": "",
        "preview_url": "",
        "download_url": "",
        "input_summary_json": "{}",
        "output_summary_json": "{}",
        "model_call_summary_json": "{}",
        "timezone_offset_minutes": 0,
        "is_deleted": 0,
        "create_time": "2026-01-01T00:00:00Z",
        "update_time": "2026-01-01T00:00:00Z",
        "remark": "",
    }
    values.update(overrides)
    return BizStageVersion(**values)


def _asset(**overrides) -> BizMaterialAsset:
    values = {
        "material_asset_id": "mat_keyframe",
        "remark": "",
        "owner_user_id": 1,
        "task_id": "",
        "workflow_id": "wf_mapper",
        "source_task_id": "",
        "source_material_id": "",
        "asset_role": "keyframe",
        "stage_type": "keyframe",
        "clip_index": 1,
        "version_no": 1,
        "selected_for_next": 1,
        "user_rating": None,
        "rating_note": "",
        "media_type": "image",
        "title": "Keyframe",
        "origin_provider": "provider",
        "origin_model": "model",
        "remote_task_id": "",
        "remote_asset_id": "",
        "original_file_name": "",
        "stored_file_name": "",
        "file_ext": "png",
        "storage_provider": "local",
        "mime_type": "image/png",
        "size_bytes": 0,
        "sha256": "",
        "duration_seconds": 0,
        "width": 1280,
        "height": 720,
        "has_audio": 0,
        "local_storage_path": "",
        "local_file_path": "",
        "public_url": "/media/keyframe.png",
        "thumbnail_url": "/media/keyframe-thumb.png",
        "third_party_url": "",
        "remote_url": "",
        "metadata_json": '{"prompt": "hello"}',
        "captured_at": "2026-01-01T00:00:00Z",
        "timezone_offset_minutes": 0,
        "create_time": "2026-01-01T00:00:00Z",
        "update_time": "2026-01-01T00:00:00Z",
        "is_deleted": 0,
    }
    values.update(overrides)
    return BizMaterialAsset(**values)


def test_workflow_view_mapper_builds_summary_and_detail() -> None:
    workflow = _workflow()
    storyboard = _version(stage_version_id="sv_story", title="Storyboard")
    keyframe = _version(
        stage_version_id="kv_1",
        stage_type="keyframe",
        clip_index=1,
        title="Keyframe 1",
        material_asset_id="mat_keyframe",
        preview_url="/media/keyframe.png",
        download_url="/media/keyframe.png",
        input_summary_json='{"variantKind": "keyframe"}',
    )
    character_sheet = _version(
        stage_version_id="kv_character",
        stage_type="keyframe",
        clip_index=1001,
        title="Character Sheet",
        input_summary_json='{"variantKind": "character_sheet"}',
    )
    final_asset = _asset(
        material_asset_id="mat_final",
        asset_role="joined",
        stage_type="joined",
        media_type="video",
        title="Final Video",
        public_url="/media/final.mp4",
        thumbnail_url="",
        has_audio=1,
    )
    mapper = WorkflowViewMapper(
        lambda _version: (
            [{"name": "A", "summary": "Hero", "appearance": "red coat"}],
            [{"clipIndex": 1, "shotLabel": "Shot 1", "scene": "intro", "targetDurationSeconds": 5}],
        )
    )

    versions = [storyboard, keyframe, character_sheet]
    summary = mapper.to_workflow_summary(workflow, versions)
    detail = mapper.to_workflow_detail(
        workflow,
        versions,
        {
            "mat_keyframe": _asset(),
            "mat_final": final_asset,
        },
    )

    assert summary["storyboardVersionCount"] == 1
    assert summary["keyframeVersionCount"] == 1
    assert summary["characterSheetVersionCount"] == 1
    assert detail["clipSlots"][0]["keyframeVersions"][0]["asset"]["id"] == "mat_keyframe"
    assert detail["characterSheets"][0]["keyframeVersions"][0]["id"] == "kv_character"
    assert detail["finalResult"]["id"] == "mat_final"
    assert detail["finalResult"]["hasAudio"] is True
