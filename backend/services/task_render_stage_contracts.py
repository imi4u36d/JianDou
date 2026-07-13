"""Value objects shared across task render-stage collaborators."""

from __future__ import annotations

from typing import Any

from backend.shared import string_value


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
        self,
        image_run_ids: list[str],
        video_run_ids: list[str],
        latest_video_output_url: str,
        clip_count: int,
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
        self._video_input_url = string_value(
            legacy_values.pop("video_input_url_value", video_input_url)
        )
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
