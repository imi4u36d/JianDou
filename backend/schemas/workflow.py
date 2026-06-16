from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class CreateWorkflowRequest(BaseModel):
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

class UpdateWorkflowSettingsRequest(BaseModel):
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

class AdjustStoryboardRequest(BaseModel):
    prompt: Optional[str] = None

class RateWorkflowRequest(BaseModel):
    effect_rating: Optional[int] = None
    effect_rating_note: Optional[str] = None

class RateStageVersionRequest(BaseModel):
    effect_rating: Optional[int] = None
    effect_rating_note: Optional[str] = None
