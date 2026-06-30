from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder


def _workflow() -> BizStageWorkflow:
    return BizStageWorkflow(
        workflow_id="wf_builder",
        owner_user_id=42,
        title="Builder Workflow",
        transcript_text="Once upon a time",
        aspect_ratio="16:9",
        text_analysis_model="text-model",
        image_model="image-model",
        video_model="video-model",
        video_size="1280*720",
        keyframe_seed=11,
        video_seed=22,
        duration_mode="auto",
        min_duration_seconds=5,
        max_duration_seconds=12,
        status="READY",
        current_stage="storyboard",
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


def test_builder_creates_storyboard_request() -> None:
    request = WorkflowGenerationRequestBuilder().build_storyboard_request(_workflow())

    assert request["kind"] == "script"
    assert request["input"]["text"] == "Once upon a time"
    assert request["model"]["textAnalysisModel"] == "text-model"
    assert "options" not in request
    assert request["auth"]["userId"] == 42


def test_builder_creates_keyframe_request_and_prompt() -> None:
    request, prompt = WorkflowGenerationRequestBuilder().build_keyframe_request(
        _workflow(),
        workflow_id="wf_builder",
        clip_index=3,
        width=1824,
        height=1024,
        character=None,
        clip={
            "shotLabel": "镜头 3",
            "startFrame": "door opens",
            "endFrame": "light fills room",
            "scene": "warehouse",
        },
    )

    assert request["kind"] == "image"
    assert request["input"]["prompt"] == prompt
    assert request["input"]["frameRole"] == "first"
    assert request["input"]["seed"] == 11
    assert request["model"]["providerModel"] == "image-model"
    assert request["metadata"] == {
        "workflowId": "wf_builder",
        "stage": "keyframe",
        "clipIndex": 3,
        "variantKind": "keyframe",
    }
    assert "Scene action: warehouse" in prompt


def test_builder_defaults_missing_image_model_to_gpt_image_2() -> None:
    workflow = _workflow()
    workflow.image_model = ""

    request, _ = WorkflowGenerationRequestBuilder().build_keyframe_request(
        workflow,
        workflow_id="wf_builder",
        clip_index=1,
        width=1824,
        height=1024,
        character=None,
        clip={"shotLabel": "镜头 1"},
    )

    assert request["model"]["providerModel"] == "gpt-image-2"


def test_builder_creates_start_keyframe_from_previous_tail_request() -> None:
    request, prompt = WorkflowGenerationRequestBuilder().build_start_keyframe_from_tail_frame_request(
        _workflow(),
        workflow_id="wf_builder",
        clip_index=2,
        width=1824,
        height=1024,
        clip={
            "shotLabel": "镜头 2",
            "startFrame": "light fills room",
            "endFrame": "door closes",
            "scene": "warehouse",
        },
        previous_tail_frame_remote_url="https://cdn.example/clip-1-last.png",
        character_sheet_urls=["https://cdn.example/character.png"],
    )

    assert request["kind"] == "image"
    assert request["input"]["prompt"] == prompt
    assert request["input"]["frameRole"] == "first"
    assert request["input"]["referenceImageUrl"] == "https://cdn.example/clip-1-last.png"
    assert request["input"]["referenceImageUrls"] == [
        "https://cdn.example/clip-1-last.png",
        "https://cdn.example/character.png",
    ]
    assert request["storage"]["fileStem"] == "clip2-first"


def test_builder_creates_character_sheet_request() -> None:
    request, prompt = WorkflowGenerationRequestBuilder().build_keyframe_request(
        _workflow(),
        workflow_id="wf_builder",
        clip_index=1001,
        width=1024,
        height=1024,
        character={"name": "阿宁", "appearance": "red coat"},
        clip=None,
    )

    assert request["input"]["frameRole"] == "sheet"
    assert request["metadata"]["variantKind"] == "character_sheet"
    assert "阿宁" in prompt
    assert "red coat" in prompt


def test_builder_creates_video_request_with_existing_prompt_shape() -> None:
    request, prompt = WorkflowGenerationRequestBuilder().build_video_request(
        _workflow(),
        workflow_id="wf_builder",
        clip_index=2,
        clip={
            "shotLabel": "镜头 2",
            "scene": "corridor",
            "startFrame": "turns back",
            "endFrame": "camera pulls away",
        },
        width=1280,
        height=720,
        duration_seconds=6,
        first_frame_url="https://cdn.example/start.png",
        last_frame_url="https://cdn.example/end.png",
    )

    assert request["kind"] == "video"
    assert request["input"]["prompt"] == prompt
    assert request["input"]["durationSeconds"] == 6
    assert request["input"]["firstFrameUrl"] == "https://cdn.example/start.png"
    assert request["input"]["lastFrameUrl"] == "https://cdn.example/end.png"
    assert request["model"]["providerModel"] == "video-model"
    assert request["metadata"] == {
        "workflowId": "wf_builder",
        "stage": "video",
        "clipIndex": 2,
    }
    assert prompt.startswith("Video clip.")
    assert "Start frame: turns back" in prompt
