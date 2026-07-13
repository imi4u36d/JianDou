"""Render-stage value objects and payload builders."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_render_stage_contracts import (
    FrameResolution as FrameResolution,
)
from backend.services.task_render_stage_contracts import (
    RenderStageRequest as RenderStageRequest,
)
from backend.services.task_render_stage_contracts import (
    RenderStageResult as RenderStageResult,
)
from backend.shared import first_non_blank, string_value


def build_frame_continuity_prompt(
    shot_plan: Any,
    prompt: str,
    start_frame_prompt: str,
    reference_image_url: str,
    frame_role: str,
) -> str:
    base_prompt = first_non_blank(
        prompt,
        _callable_attr(shot_plan, "last_frame_prompt"),
        _callable_attr(shot_plan, "first_frame_prompt"),
        _callable_attr(shot_plan, "video_prompt"),
        _callable_attr(shot_plan, "scene"),
    )
    if frame_role.lower() != "last" or not string_value(reference_image_url):
        return base_prompt

    parts: list[str] = [
        "你现在要生成同一镜头连续动作后的尾帧，必须严格沿用参考图已经确定的同一场景、同一机位体系、同一空间锚点、同一人物外观与服装、同一道具位置关系，禁止漂移到新的场景。",
        "尾帧只允许在参考首帧基础上推进人物动作状态、视线方向、手部位置或道具使用结果，禁止新增、删除或替换背景布局、门窗桌椅书架等场景元素。",
    ]
    resolved_start_frame_prompt = first_non_blank(
        start_frame_prompt,
        _callable_attr(shot_plan, "first_frame_prompt"),
        _callable_attr(shot_plan, "last_frame_prompt"),
    )
    if resolved_start_frame_prompt:
        parts.append(f"参考首帧描述：{resolved_start_frame_prompt}")
        parts.append(f"场景锁定基准：{resolved_start_frame_prompt}")
    scene = _callable_attr(shot_plan, "scene")
    if scene:
        parts.append(f"场景锚点：{scene}")
    camera = _callable_attr(shot_plan, "camera_movement")
    if camera and camera.lower() != "static":
        parts.append(f"运镜：{camera}")
    if base_prompt:
        parts.append(f"尾帧目标：{base_prompt}")
    return "\n".join(parts)


def build_planning_stage_request(
    task: TaskRecord,
    clip_prompt: str,
    first_frame_prompt: str,
    last_frame_prompt: str,
    clip_duration_seconds: int,
) -> dict[str, Any]:
    snapshot = task.request_snapshot or {}
    return {
        "aspectRatio": snapshot.get("aspectRatio", task.aspect_ratio),
        "clipPrompt": _truncate_text(clip_prompt, 160),
        "firstFramePrompt": _truncate_text(first_frame_prompt, 160),
        "lastFramePrompt": _truncate_text(last_frame_prompt, 160),
        "targetDurationSeconds": clip_duration_seconds,
    }


def build_planning_stage_response(
    start_frame: FrameResolution,
    end_frame: FrameResolution,
    reused_previous_start: bool,
) -> dict[str, Any]:
    return {
        "summary": "已复用上一镜尾帧作为首帧，并生成当前镜头尾帧关键画面"
        if reused_previous_start
        else "当前镜头首尾关键画面已生成",
        "imageRunId": first_non_blank(start_frame.run_id(), end_frame.run_id()),
        "imageUrl": start_frame.material_url(),
        "remoteImageUrl": start_frame.video_input_url(),
        "startFrameUrl": start_frame.video_input_url(),
        "startFrameSourceType": start_frame.source_type(),
        "startFrameSourceUrl": start_frame.source_url(),
        "startFrameKeyframeUrl": start_frame.material_url(),
        "startFrameImageRunId": start_frame.run_id(),
        "endFrameConstraintUrl": end_frame.video_input_url(),
        "endFrameSourceType": end_frame.source_type(),
        "endFrameSourceUrl": end_frame.source_url(),
        "endFrameKeyframeUrl": end_frame.material_url(),
        "endFrameImageRunId": end_frame.run_id(),
    }


def build_render_stage_request(
    start_frame: FrameResolution,
    end_frame: FrameResolution,
    clip_duration_seconds: int,
) -> dict[str, Any]:
    return {
        "imageRunId": first_non_blank(start_frame.run_id(), end_frame.run_id()),
        "posterUrl": start_frame.material_url(),
        "targetDurationSeconds": clip_duration_seconds,
        "firstFrameUrl": start_frame.video_input_url(),
        "firstFrameSourceType": start_frame.source_type(),
        "requestedLastFrameUrl": end_frame.video_input_url(),
        "requestedLastFrameSourceType": end_frame.source_type(),
    }


def build_render_stage_response(
    video_run: dict[str, Any],
    video_material: dict[str, Any],
    video_metadata: dict[str, Any],
    resolved_first_frame_url: str,
    resolved_last_frame_url: str,
    resolved_last_frame_source_type: str,
    requested_last_frame_url: str,
) -> dict[str, Any]:
    return {
        "videoRunId": string_value(video_run.get("id")),
        "outputUrl": string_value(video_material.get("fileUrl")),
        "remoteTaskId": string_value(video_metadata.get("taskId")),
        "firstFrameUrl": resolved_first_frame_url,
        "requestedLastFrameUrl": requested_last_frame_url,
        "lastFrameUrl": resolved_last_frame_url,
        "lastFrameSourceType": resolved_last_frame_source_type,
    }


def build_clip_frame_context(
    shot_plan: Any,
    clip_index: int,
    clip_duration_seconds: int,
    start_frame: FrameResolution,
    end_frame: FrameResolution,
    video_run_id: str,
    video_output_url: str,
    resolved_last_frame_url: str,
    resolved_last_frame_source_type: str,
) -> dict[str, Any]:
    return {
        "clipIndex": clip_index,
        "shotLabel": _callable_attr(shot_plan, "shot_label"),
        "scene": _callable_attr(shot_plan, "scene"),
        "targetDurationSeconds": clip_duration_seconds,
        "startFramePrompt": first_non_blank(
            start_frame.prompt(),
            _callable_attr(shot_plan, "first_frame_prompt"),
            _callable_attr(shot_plan, "last_frame_prompt"),
        ),
        "startFrameUrl": start_frame.video_input_url(),
        "startFrameSourceType": start_frame.source_type(),
        "startFrameSourceUrl": start_frame.source_url(),
        "startFrameKeyframeUrl": start_frame.material_url(),
        "startFrameKeyframeRemoteSourceUrl": start_frame.remote_url(),
        "startFrameKeyframeRunId": start_frame.run_id(),
        "endFramePrompt": first_non_blank(end_frame.prompt(), _callable_attr(shot_plan, "last_frame_prompt")),
        "endFrameConstraintUrl": end_frame.video_input_url(),
        "endFrameSourceType": end_frame.source_type(),
        "endFrameSourceUrl": end_frame.source_url(),
        "endFrameKeyframeUrl": end_frame.material_url(),
        "endFrameKeyframeRemoteSourceUrl": end_frame.remote_url(),
        "endFrameKeyframeRunId": end_frame.run_id(),
        "videoRunId": video_run_id,
        "videoOutputUrl": video_output_url,
        "returnedLastFrameUrl": resolved_last_frame_url,
        "returnedLastFrameSourceType": resolved_last_frame_source_type,
    }


def resolved_last_frame_source_type(
    extracted_last_frame_url: str,
    provider_requested_last_frame_url: str,
    requested_last_frame_url: str,
) -> str:
    if string_value(extracted_last_frame_url):
        return "video_result_last_frame"
    if string_value(provider_requested_last_frame_url):
        return "video_requested_last_frame"
    if string_value(requested_last_frame_url):
        return "end_frame_keyframe_fallback"
    return ""


def resolved_last_frame_source_url(
    extracted_last_frame_url: str,
    provider_requested_last_frame_url: str,
    requested_last_frame_url: str,
) -> str:
    return first_non_blank(extracted_last_frame_url, provider_requested_last_frame_url, requested_last_frame_url)


def _callable_attr(source: Any, name: str) -> str:
    value = getattr(source, name, "")
    if callable(value):
        value = value()
    return string_value(value)


def _truncate_text(value: str, max_length: int) -> str:
    if not value:
        return ""
    normalized = value.replace("\n", " ").strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length] + "..."
