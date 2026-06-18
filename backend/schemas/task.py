from __future__ import annotations
from pydantic import AliasGenerator, BaseModel, ConfigDict
from typing import Any, Optional


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class TaskListItemResponse(BaseModel):
    id: str = ""
    task_type: str = ""
    title: str = ""
    status: str = ""
    progress: int = 0
    created_at: str = ""
    updated_at: str = ""
    source_file_name: str = ""
    aspect_ratio: str = ""
    min_duration_seconds: int = 0
    max_duration_seconds: int = 0
    retry_count: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    completed_output_count: int = 0
    task_seed: Optional[int] = None
    effect_rating: Optional[int] = None
    effect_rating_note: str = ""
    rated_at: Optional[str] = None
    has_transcript: bool = False
    has_timed_transcript: bool = False
    source_asset_count: int = 0
    editing_mode: str = ""
    is_queued: bool = False
    queue_position: Optional[int] = None
    current_stage: str = ""
    active_worker_instance_id: str = ""
    planned_clip_count: int = 0
    rendered_clip_count: int = 0
    diagnosis_severity: str = ""
    diagnosis_code: str = ""
    diagnosis_hint: str = ""
    recommended_action: str = ""
    failure_reason: str = ""
    failure_stage: str = ""
    failure_clip_index: Optional[int] = None
    thumbnail_url: str = ""
    owner_user_id: Optional[int] = None
    owner_username: str = ""
    owner_display_name: str = ""
    owner_role: str = ""

class TaskDetailResponse(BaseModel):
    id: str = ""
    task_type: str = ""
    title: str = ""
    status: str = ""
    progress: int = 0
    created_at: str = ""
    updated_at: str = ""
    source_file_name: str = ""
    aspect_ratio: str = ""
    min_duration_seconds: int = 0
    max_duration_seconds: int = 0
    retry_count: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    completed_output_count: int = 0
    task_seed: Optional[int] = None
    effect_rating: Optional[int] = None
    effect_rating_note: str = ""
    rated_at: Optional[str] = None
    is_queued: bool = False
    queue_position: Optional[int] = None
    current_stage: str = ""
    active_worker_instance_id: str = ""
    owner_user_id: Optional[int] = None
    owner_username: str = ""
    owner_display_name: str = ""
    error_message: Optional[str] = None
    editing_mode: str = ""
    trace: list = []
    status_history: list = []
    attempts: list = []
    stage_runs: list = []
    model_calls: list = []
    materials: list = []
    outputs: list = []
    source_assets: list = []

class CreateGenerationTaskRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    title: str
    task_type: Optional[str] = None
    asset_type: Optional[str] = None
    creative_prompt: Optional[str] = None
    aspect_ratio: Optional[str] = None
    image_size: Optional[str] = None
    text_analysis_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    video_size: Optional[str] = None
    seed: Optional[int] = None
    video_duration_seconds: Optional[Any] = None
    output_count: Optional[Any] = None
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    transcript_text: Optional[str] = None
    stop_before_video_generation: Optional[bool] = None
    reference_image_urls: Optional[list[str]] = None
    reference_asset_ids: Optional[list[str]] = None

class GenerateCreativePromptRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    title: str
    aspect_ratio: Optional[str] = None
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    intro_template: Optional[str] = None
    outro_template: Optional[str] = None
    transcript_text: Optional[str] = None

class RateTaskEffectRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    effect_rating: Optional[int] = None
    effect_rating_note: Optional[str] = None

class TaskDeleteResult(BaseModel):
    success: bool = False
    task_id: str = ""
