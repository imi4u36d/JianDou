from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.service

from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory


def _workflow() -> BizStageWorkflow:
    return BizStageWorkflow(
        workflow_id="wf_factory",
        owner_user_id=7,
        title="Factory Workflow",
        transcript_text="",
        aspect_ratio="16:9",
        style_preset="cinematic",
        text_analysis_model="",
        image_model="",
        video_model="",
        video_size="1280*720",
        duration_mode="auto",
        min_duration_seconds=5,
        max_duration_seconds=12,
        status="READY",
        current_stage="keyframe",
        selected_storyboard_version_id="",
        final_join_asset_id="",
        effect_rating=None,
        effect_rating_note="",
        metadata_json="{}",
        timezone_offset_minutes=0,
        create_time="2026-01-01T00:00:00Z",
        update_time="2026-01-01T00:00:00Z",
        is_deleted=0,
        remark="",
    )


def test_row_factory_creates_image_material_asset_defaults() -> None:
    row = WorkflowPersistenceRowFactory(
        now=lambda: "2026-01-02T00:00:00Z",
        random_id=lambda: "abcdef1234567890zzzz",
    ).create_material_asset(
        wf=_workflow(),
        stage_type="keyframe",
        clip_index=2,
        version_no=3,
        media_type="image",
        title="Keyframe",
        public_url="/media/keyframe.png",
        mime_type="image/png",
        width=1280,
        height=720,
        origin_provider="provider",
        origin_model="model",
        remote_url="https://remote.example/keyframe.png",
        metadata={"prompt": "hello"},
    )

    assert row.material_asset_id == "mat_abcdef1234567890"
    assert row.owner_user_id == 7
    assert row.workflow_id == "wf_factory"
    assert row.asset_role == "keyframe"
    assert row.stage_type == "keyframe"
    assert row.clip_index == 2
    assert row.version_no == 3
    assert row.selected_for_next == 1
    assert row.has_audio == 0
    assert row.public_url == "/media/keyframe.png"
    assert row.thumbnail_url == "/media/keyframe.png"
    assert row.remote_url == "https://remote.example/keyframe.png"
    assert json.loads(row.metadata_json) == {"prompt": "hello"}
    assert row.create_time == "2026-01-02T00:00:00Z"
    assert row.update_time == "2026-01-02T00:00:00Z"


def test_row_factory_creates_video_material_asset_audio_flag() -> None:
    row = WorkflowPersistenceRowFactory(
        now=lambda: "2026-01-02T00:00:00Z",
        random_id=lambda: "video1234567890xx",
    ).create_material_asset(
        wf=_workflow(),
        stage_type="video",
        clip_index=1,
        version_no=1,
        media_type="video",
        title="Video",
        public_url="/media/video.mp4",
        mime_type="video/mp4",
        duration_seconds=6.0,
    )

    assert row.material_asset_id == "mat_video1234567890x"
    assert row.has_audio == 1
    assert row.thumbnail_url == ""
    assert row.duration_seconds == 6.0


def test_row_factory_creates_stage_version_with_json_summaries() -> None:
    row = WorkflowPersistenceRowFactory(
        now=lambda: "2026-01-02T00:00:00Z",
        random_id=lambda: "unused",
    ).create_stage_version(
        wf=_workflow(),
        stage_version_id="kv_factory",
        stage_type="keyframe",
        clip_index=2,
        version_no=3,
        title="Keyframe Version",
        status="COMPLETED",
        selected=1,
        material_asset_id="mat_keyframe",
        preview_url="/media/keyframe.png",
        download_url="/media/keyframe.png",
        input_summary={"clipIndex": 2},
        output_summary={"fileUrl": "/media/keyframe.png"},
        model_call_summary={"runId": "run_1"},
    )

    assert row.stage_version_id == "kv_factory"
    assert row.workflow_id == "wf_factory"
    assert row.owner_user_id == 7
    assert row.stage_type == "keyframe"
    assert row.clip_index == 2
    assert row.version_no == 3
    assert row.selected == 1
    assert row.rating_note == ""
    assert row.parent_version_id == ""
    assert row.material_asset_id == "mat_keyframe"
    assert json.loads(row.input_summary_json) == {"clipIndex": 2}
    assert json.loads(row.output_summary_json) == {"fileUrl": "/media/keyframe.png"}
    assert json.loads(row.model_call_summary_json) == {"runId": "run_1"}
    assert row.create_time == "2026-01-02T00:00:00Z"
    assert row.update_time == "2026-01-02T00:00:00Z"


def test_row_factory_creates_stage_version_empty_summaries() -> None:
    row = WorkflowPersistenceRowFactory(
        now=lambda: "2026-01-02T00:00:00Z",
        random_id=lambda: "unused",
    ).create_stage_version(
        wf=_workflow(),
        stage_version_id="sv_empty",
        stage_type="storyboard",
        clip_index=0,
        version_no=1,
        title="Storyboard",
        status="COMPLETED",
    )

    assert row.material_asset_id == ""
    assert row.preview_url == ""
    assert row.download_url == ""
    assert row.input_summary_json == "{}"
    assert row.output_summary_json == "{}"
    assert row.model_call_summary_json == "{}"
