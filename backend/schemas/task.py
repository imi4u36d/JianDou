from __future__ import annotations

from typing import Any

from pydantic import AliasGenerator, BaseModel, ConfigDict

from backend.schemas.common import _to_camel, camel_alias


class TaskListItemResponse(BaseModel):
    model_config = ConfigDict(alias_generator=camel_alias, populate_by_name=True)

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
    started_at: str | None = None
    finished_at: str | None = None
    completed_output_count: int = 0
    task_seed: int | None = None
    effect_rating: int | None = None
    effect_rating_note: str = ""
    rated_at: str | None = None
    has_transcript: bool = False
    has_timed_transcript: bool = False
    source_asset_count: int = 0
    editing_mode: str = ""
    is_queued: bool = False
    queue_position: int | None = None
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
    failure_clip_index: int | None = None
    thumbnail_url: str = ""
    owner_user_id: int | None = None
    owner_username: str = ""
    owner_role: str = ""

class TaskDetailResponse(BaseModel):
    model_config = ConfigDict(alias_generator=camel_alias, populate_by_name=True)

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
    started_at: str | None = None
    finished_at: str | None = None
    completed_output_count: int = 0
    task_seed: int | None = None
    effect_rating: int | None = None
    effect_rating_note: str = ""
    rated_at: str | None = None
    is_queued: bool = False
    queue_position: int | None = None
    current_stage: str = ""
    active_worker_instance_id: str = ""
    owner_user_id: int | None = None
    owner_username: str = ""
    error_message: str | None = None
    editing_mode: str = ""
    trace: list = []
    status_history: list = []
    attempts: list = []
    stage_runs: list = []
    model_calls: list = []
    materials: list = []
    outputs: list = []
    source_assets: list = []
    creative_prompt: str = ""
    has_transcript: bool = False
    has_timed_transcript: bool = False
    source_asset_count: int = 0
    transcript_preview: str | None = None
    transcript_cue_count: int = 0
    execution_context: dict[str, Any] = {}
    request_snapshot: dict[str, Any] = {}
    storyboard_script: str = ""
    artifact_directories: dict[str, Any] = {}
    duration_diagnostics: list = []
    plan: list = []

class CreateGenerationTaskRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    title: str
    task_type: str | None = None
    asset_type: str | None = None
    creative_prompt: str | None = None
    aspect_ratio: str | None = None
    image_size: str | None = None
    text_analysis_model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    video_size: str | None = None
    seed: int | None = None
    video_duration_seconds: Any | None = None
    output_count: Any | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    transcript_text: str | None = None
    stop_before_video_generation: bool | None = None
    reference_image_urls: list[str] | None = None
    reference_asset_ids: list[str] | None = None

class GenerateCreativePromptRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    title: str
    aspect_ratio: str | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    intro_template: str | None = None
    outro_template: str | None = None
    transcript_text: str | None = None

class RateTaskEffectRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    effect_rating: int | None = None
    effect_rating_note: str | None = None

class TaskDeleteResult(BaseModel):
    success: bool = False
    task_id: str = ""


class GenerateCreativePromptResponse(BaseModel):
    prompt: str = ""
    source: str = "default"
