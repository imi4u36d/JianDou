from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.domain.task_storyboard_planner import ShotPlan
from backend.services.task_render_stage_contracts import FrameResolution as ContractFrameResolution
from backend.services.task_render_stage_payloads import (
    FrameResolution,
    RenderStageRequest,
    RenderStageResult,
    build_clip_frame_context,
    build_frame_continuity_prompt,
    build_planning_stage_request,
    build_planning_stage_response,
    build_render_stage_request,
    build_render_stage_response,
    resolved_last_frame_source_type,
    resolved_last_frame_source_url,
)

pytestmark = pytest.mark.service


def test_payload_module_preserves_render_contract_exports() -> None:
    assert FrameResolution is ContractFrameResolution


def test_render_stage_request_uses_isolated_default_lists() -> None:
    first = RenderStageRequest()
    second = RenderStageRequest()

    first.shot_plans.append("shot")
    first.clip_duration_plan.append([1, 2, 3])
    first.existing_video_clip_indices.append(1)

    assert second.shot_plans == []
    assert second.clip_duration_plan == []
    assert second.existing_video_clip_indices == []


def test_render_stage_request_and_result_expose_pipeline_contract() -> None:
    request = RenderStageRequest(
        reuse_storyboard=True,
        render_start_index=3,
        completed_clip_count=2,
        requested_resume_stage="render",
        requested_resume_clip_index=3,
        existing_video_clip_indices=[1, 2],
        shot_plans=["shot-a"],
        clip_duration_plan=[[6, 4, 8]],
        width=1280,
        height=720,
        duration_seconds=12,
        video_size="1280*720",
        previous_clip_last_frame_url="https://cdn.example.test/last.png",
    )
    result = RenderStageResult(["image-1"], ["video-1"], "https://cdn.example.test/out.mp4", 1)

    assert request.reuse_storyboard is True
    assert request.render_start_index == 3
    assert request.completed_clip_count == 2
    assert request.requested_resume_stage == "render"
    assert request.requested_resume_clip_index == 3
    assert request.existing_video_clip_indices == [1, 2]
    assert request.shot_plans == ["shot-a"]
    assert request.clip_duration_plan == [[6, 4, 8]]
    assert request.width == 1280
    assert request.height == 720
    assert request.duration_seconds == 12
    assert request.video_size == "1280*720"
    assert request.previous_clip_last_frame_url == "https://cdn.example.test/last.png"
    assert result.image_run_ids == ["image-1"]
    assert result.video_run_ids == ["video-1"]
    assert result.latest_video_output_url == "https://cdn.example.test/out.mp4"
    assert result.clip_count == 1


def test_build_frame_continuity_prompt_locks_scene_for_last_frame_with_reference() -> None:
    shot_plan = ShotPlan(
        shot_label="S1",
        scene="library desk",
        first_frame_prompt="hero reads a letter",
        last_frame_prompt="hero closes the letter",
        camera_movement="slow push",
        video_prompt="a quiet reveal",
    )

    prompt = build_frame_continuity_prompt(
        shot_plan,
        "hero looks up",
        "hero reads a letter",
        "https://cdn.example.test/start.png",
        "last",
    )

    assert "同一镜头连续动作后的尾帧" in prompt
    assert "参考首帧描述：hero reads a letter" in prompt
    assert "场景锚点：library desk" in prompt
    assert "运镜：slow push" in prompt
    assert "尾帧目标：hero looks up" in prompt


def test_build_frame_continuity_prompt_returns_base_prompt_when_not_last_frame() -> None:
    shot_plan = ShotPlan(last_frame_prompt="fallback last", first_frame_prompt="fallback first")

    prompt = build_frame_continuity_prompt(shot_plan, "", "", "https://cdn.example.test/ref.png", "first")

    assert prompt == "fallback last"


def test_build_stage_payloads_from_frames() -> None:
    task = _task()
    start_frame = _frame(
        run_id="image-start",
        source_type="generated_start_frame_keyframe",
        source_url="https://remote.example.test/start.png",
        material_url="/storage/start.png",
        remote_url="https://cdn.example.test/start.png",
        video_input_url="https://cdn.example.test/start.png",
    )
    end_frame = _frame(
        prompt="end prompt",
        run_id="image-end",
        source_type="generated_end_frame_keyframe",
        source_url="https://remote.example.test/end.png",
        material_url="/storage/end.png",
        remote_url="https://cdn.example.test/end.png",
        video_input_url="https://cdn.example.test/end.png",
    )

    request = build_planning_stage_request(task, "clip\nprompt", "first", "last", 8)
    planning_response = build_planning_stage_response(start_frame, end_frame, reused_previous_start=True)
    render_request = build_render_stage_request(start_frame, end_frame, 8)
    render_response = build_render_stage_response(
        {"id": "video-run"},
        {"fileUrl": "/storage/video.mp4"},
        {"taskId": "remote-task"},
        "https://cdn.example.test/start.png",
        "https://cdn.example.test/last.png",
        "video_result_last_frame",
        "https://cdn.example.test/end.png",
    )

    assert request == {
        "aspectRatio": "9:16",
        "clipPrompt": "clip prompt",
        "firstFramePrompt": "first",
        "lastFramePrompt": "last",
        "targetDurationSeconds": 8,
    }
    assert planning_response["summary"] == "已复用上一镜尾帧作为首帧，并生成当前镜头尾帧关键画面"
    assert planning_response["imageRunId"] == "image-start"
    assert planning_response["endFrameConstraintUrl"] == "https://cdn.example.test/end.png"
    assert render_request["requestedLastFrameSourceType"] == "generated_end_frame_keyframe"
    assert render_response == {
        "videoRunId": "video-run",
        "outputUrl": "/storage/video.mp4",
        "remoteTaskId": "remote-task",
        "firstFrameUrl": "https://cdn.example.test/start.png",
        "requestedLastFrameUrl": "https://cdn.example.test/end.png",
        "lastFrameUrl": "https://cdn.example.test/last.png",
        "lastFrameSourceType": "video_result_last_frame",
    }


def test_build_clip_frame_context_preserves_frame_and_video_details() -> None:
    shot_plan = ShotPlan(shot_label="S2", scene="office", first_frame_prompt="first prompt", last_frame_prompt="last prompt")

    context = build_clip_frame_context(
        shot_plan,
        clip_index=2,
        clip_duration_seconds=6,
        start_frame=_frame(video_input_url="https://cdn.example.test/start.png", source_type="previous_video_last_frame"),
        end_frame=_frame(prompt="generated end", video_input_url="https://cdn.example.test/end.png", run_id="image-end"),
        video_run_id="video-run",
        video_output_url="/storage/clip2.mp4",
        resolved_last_frame_url="https://cdn.example.test/returned-last.png",
        resolved_last_frame_source_type="video_result_last_frame",
    )

    assert context["clipIndex"] == 2
    assert context["shotLabel"] == "S2"
    assert context["startFramePrompt"] == "first prompt"
    assert context["endFramePrompt"] == "generated end"
    assert context["videoRunId"] == "video-run"
    assert context["videoOutputUrl"] == "/storage/clip2.mp4"
    assert context["returnedLastFrameUrl"] == "https://cdn.example.test/returned-last.png"


def test_resolved_last_frame_source_prefers_extracted_then_provider_then_requested() -> None:
    assert (
        resolved_last_frame_source_type("https://cdn.example.test/extracted.png", "provider.png", "requested.png")
        == "video_result_last_frame"
    )
    assert resolved_last_frame_source_type("", "provider.png", "requested.png") == "video_requested_last_frame"
    assert resolved_last_frame_source_type("", "", "requested.png") == "end_frame_keyframe_fallback"
    assert resolved_last_frame_source_type("", "", "") == ""

    assert (
        resolved_last_frame_source_url("", "https://cdn.example.test/provider.png", "https://cdn.example.test/requested.png")
        == "https://cdn.example.test/provider.png"
    )


def _task(**overrides: Any) -> TaskRecord:
    values = {
        "id": "task_payload",
        "owner_user_id": 11,
        "title": "Payload Task",
        "status": TaskStatus.RENDERING.value,
        "aspect_ratio": "16:9",
        "creative_prompt": "Create something",
        "transcript_text": "Transcript text",
        "task_type": "video_generation",
        "request_snapshot": {"aspectRatio": "9:16"},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    return TaskRecord(**values)


def _frame(**overrides: Any) -> FrameResolution:
    values = {
        "prompt": "",
        "frame_role": "first",
        "source_type": "generated_start_frame_keyframe",
        "source_url": "https://remote.example.test/frame.png",
        "material_url": "/storage/frame.png",
        "remote_url": "https://cdn.example.test/frame.png",
        "video_input_url": "https://cdn.example.test/frame.png",
        "run_id": "image-run",
        "material": {"fileUrl": "/storage/frame.png"},
    }
    values.update(overrides)
    return FrameResolution(**values)
