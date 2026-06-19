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
