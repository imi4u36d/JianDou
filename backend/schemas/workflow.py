from __future__ import annotations

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field

from backend.schemas.common import _to_camel


class WorkflowRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
        populate_by_name=True,
    )

    def to_service_dict(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateWorkflowRequest(WorkflowRequestModel):
    title: str
    transcript_text: str | None = None
    aspect_ratio: str | None = None
    style_preset: str | None = None
    text_analysis_model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    video_size: str | None = None
    keyframe_seed: int | None = None
    video_seed: int | None = None
    seed: int | None = None
    duration_mode: str | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    execution_mode: str = "manual"


class WorkflowSummaryResponse(BaseModel):
    id: str
    title: str = ""
    status: str = ""
    current_stage: str = ""
    aspect_ratio: str = ""
    effect_rating: int | None = None
    created_at: str = ""
    updated_at: str = ""
    storyboard_version_count: int = 0
    character_sheet_count: int = 0
    selected_character_sheet_count: int = 0
    character_sheet_version_count: int = 0
    keyframe_version_count: int = 0
    video_version_count: int = 0
    execution_mode: str = "manual"
    auto_pilot_state: str = "idle"
    queue_position: int | None = None
    queue_size: int | None = None


class UpdateWorkflowSettingsRequest(WorkflowRequestModel):
    aspect_ratio: str | None = None
    style_preset: str | None = None
    text_analysis_model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    video_size: str | None = None
    keyframe_seed: int | None = None
    video_seed: int | None = None
    duration_mode: str | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None


class AdjustStoryboardRequest(WorkflowRequestModel):
    prompt: str | None = None


class SelectCharacterSheetAssetRequest(WorkflowRequestModel):
    asset_id: str = Field(min_length=1)


class RateWorkflowRequest(WorkflowRequestModel):
    effect_rating: int = Field(ge=1, le=5)
    effect_rating_note: str | None = None


class RateStageVersionRequest(WorkflowRequestModel):
    effect_rating: int = Field(ge=1, le=5)
    effect_rating_note: str | None = None


class WorkflowDeleteResult(BaseModel):
    deleted: bool = False
    workflow_id: str = ""

WorkflowListResponse = list[WorkflowSummaryResponse]


class WorkflowDetailResponse(BaseModel):
    """Full workflow detail returned by get/create/update endpoints."""
    id: str = ""
    title: str = ""
    status: str = ""
    current_stage: str = ""
    aspect_ratio: str = ""
    transcript_text: str | None = None
    style_preset: str | None = None
    video_size: str | None = None
    duration_mode: str | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    effect_rating: int | None = None
    created_at: str = ""
    updated_at: str = ""
    execution_mode: str = "manual"
    auto_pilot_state: str = "idle"
    auto_pilot_next_stage: str = ""
    auto_pilot_error_message: str = ""
    auto_pilot_started_at: str = ""
    auto_pilot_paused_at: str = ""
    queue_position: int | None = None
    queue_size: int | None = None

    model_config = ConfigDict(extra="allow")


class WorkflowActionResponse(BaseModel):
    """Generic response for workflow action endpoints (generate, select, rate, finalize)."""
    id: str = ""
    status: str = ""
    current_stage: str = ""
    updated_at: str = ""

    model_config = ConfigDict(extra="allow")
