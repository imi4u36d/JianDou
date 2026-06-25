"""Render-stage value objects and payload builders."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import first_non_blank, string_value


class RenderStageRequest:
    def __init__(
        self,
        reuse_storyboard: bool = False,
        render_start_index: int = 1,
        completed_clip_count: int = 0,
        requested_resume_stage: str = "",
        requested_resume_clip_index: int = 0,
        existing_video_clip_indices: list[int] | None = None,
        shot_plans: list[Any] | None = None,
        clip_duration_plan: list[list[int]] | None = None,
        width: int = 0,
        height: int = 0,
        duration_seconds: int = 0,
        video_size: str = "",
        previous_clip_last_frame_url: str = "",
        character_definitions: list[Any] | None = None,
    ) -> None:
        self._reuse_storyboard = reuse_storyboard
        self._render_start_index = render_start_index
        self._completed_clip_count = completed_clip_count
        self._requested_resume_stage = requested_resume_stage
        self._requested_resume_clip_index = requested_resume_clip_index
        self._existing_video_clip_indices = existing_video_clip_indices or []
        self._shot_plans = shot_plans or []
        self._clip_duration_plan = clip_duration_plan or []
        self._width = width
        self._height = height
        self._duration_seconds = duration_seconds
        self._video_size = video_size
        self._previous_clip_last_frame_url = previous_clip_last_frame_url
        self._character_definitions = character_definitions or []

    @property
    def reuse_storyboard(self) -> bool:
        return self._reuse_storyboard

    @property
    def render_start_index(self) -> int:
        return self._render_start_index

    @property
    def completed_clip_count(self) -> int:
        return self._completed_clip_count

    @property
    def requested_resume_stage(self) -> str:
        return self._requested_resume_stage

    @property
    def requested_resume_clip_index(self) -> int:
        return self._requested_resume_clip_index

    @property
    def existing_video_clip_indices(self) -> list[int]:
        return self._existing_video_clip_indices

    @property
    def shot_plans(self) -> list[Any]:
        return self._shot_plans

    @property
    def clip_duration_plan(self) -> list[list[int]]:
        return self._clip_duration_plan

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def duration_seconds(self) -> int:
        return self._duration_seconds

    @property
    def video_size(self) -> str:
        return self._video_size

    @property
    def previous_clip_last_frame_url(self) -> str:
        return self._previous_clip_last_frame_url

    @property
    def character_definitions(self) -> list[Any]:
        return self._character_definitions


class RenderStageResult:
    def __init__(
        self, image_run_ids: list[str], video_run_ids: list[str], latest_video_output_url: str, clip_count: int
    ) -> None:
        self._image_run_ids = image_run_ids
        self._video_run_ids = video_run_ids
        self._latest_video_output_url = latest_video_output_url
        self._clip_count = clip_count

    @property
    def image_run_ids(self) -> list[str]:
        return self._image_run_ids

    @property
    def video_run_ids(self) -> list[str]:
        return self._video_run_ids

    @property
    def latest_video_output_url(self) -> str:
        return self._latest_video_output_url

    @property
    def clip_count(self) -> int:
        return self._clip_count


class FrameResolution:
    def __init__(
        self,
        prompt: str = "",
        frame_role: str = "",
        source_type: str = "",
        source_url: str = "",
        material_url: str = "",
        remote_url: str = "",
        video_input_url: str = "",
        run_id: str = "",
        material: dict[str, Any] | None = None,
        **legacy_values: Any,
    ) -> None:
        self._prompt = string_value(legacy_values.pop("prompt_value", prompt))
        self._frame_role = string_value(legacy_values.pop("frame_role_value", frame_role))
        self._source_type = string_value(legacy_values.pop("source_type_value", source_type))
        self._source_url = string_value(legacy_values.pop("source_url_value", source_url))
        self._material_url = string_value(legacy_values.pop("material_url_value", material_url))
        self._remote_url = string_value(legacy_values.pop("remote_url_value", remote_url))
        self._video_input_url = string_value(legacy_values.pop("video_input_url_value", video_input_url))
        self._run_id = string_value(legacy_values.pop("run_id_value", run_id))
        self._material = legacy_values.pop("material_value", material) or {}
        if legacy_values:
            keys = ", ".join(sorted(legacy_values))
            raise TypeError(f"Unexpected FrameResolution arguments: {keys}")

    def prompt(self) -> str:
        return self._prompt

    def frame_role(self) -> str:
        return self._frame_role

    def source_type(self) -> str:
        return self._source_type

    def source_url(self) -> str:
        return self._source_url

    def material_url(self) -> str:
        return self._material_url

    def remote_url(self) -> str:
        return self._remote_url

    def video_input_url(self) -> str:
        return self._video_input_url

    def run_id(self) -> str:
        return self._run_id

    def material(self) -> dict[str, Any]:
        return self._material


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
