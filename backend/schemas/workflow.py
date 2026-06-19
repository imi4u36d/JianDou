from __future__ import annotations

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class WorkflowRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel, serialization_alias=_to_camel),
        populate_by_name=True,
    )

    def to_service_dict(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateWorkflowRequest(WorkflowRequestModel):
    title: str
    transcript_text: Optional[str] = None
    aspect_ratio: Optional[str] = None
    style_preset: Optional[str] = None
    text_analysis_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    video_size: Optional[str] = None
    keyframe_seed: Optional[int] = None
    video_seed: Optional[int] = None
    seed: Optional[int] = None
    duration_mode: Optional[str] = None
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None


class WorkflowSummaryResponse(BaseModel):
    id: str
    title: str = ""
    status: str = ""
    current_stage: str = ""
    aspect_ratio: str = ""
    effect_rating: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""
    storyboard_version_count: int = 0
    character_sheet_count: int = 0
    selected_character_sheet_count: int = 0
    character_sheet_version_count: int = 0
    keyframe_version_count: int = 0
    video_version_count: int = 0


class UpdateWorkflowSettingsRequest(WorkflowRequestModel):
    aspect_ratio: Optional[str] = None
    style_preset: Optional[str] = None
    text_analysis_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    video_size: Optional[str] = None
    keyframe_seed: Optional[int] = None
    video_seed: Optional[int] = None
    duration_mode: Optional[str] = None
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None


class AdjustStoryboardRequest(WorkflowRequestModel):
    prompt: Optional[str] = None


class SelectCharacterSheetAssetRequest(WorkflowRequestModel):
    asset_id: str = Field(min_length=1)


class RateWorkflowRequest(WorkflowRequestModel):
    effect_rating: int = Field(ge=1, le=5)
    effect_rating_note: Optional[str] = None


class RateStageVersionRequest(WorkflowRequestModel):
    effect_rating: int = Field(ge=1, le=5)
    effect_rating_note: Optional[str] = None
