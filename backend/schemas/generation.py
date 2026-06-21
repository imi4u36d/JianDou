from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerationOptionsResponse(BaseModel):
    aspect_ratios: list = []
    style_presets: list = []
    image_sizes: list = []
    video_sizes: list = []
    video_durations: list = []
    text_analysis_models: list = []
    image_models: list = []
    video_models: list = []
    default_aspect_ratio: str | None = None
    default_style_preset: str | None = None
    default_image_size: str | None = None
    default_video_size: str | None = None
    default_video_duration_seconds: int | None = None
    default_text_analysis_model: str | None = None


class GenerationRunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str = "probe"
    auth: dict[str, Any] = Field(default_factory=dict)


class GenerationRunResponse(BaseModel):
    """Flexible response model for generation run endpoints."""
    id: str = ""
    kind: str = ""
    status: str = ""
    created_at: str = ""
    updated_at: str = ""

    model_config = ConfigDict(extra="allow")


class GenerationRunListResponse(BaseModel):
    """Response model for list generation runs."""
    items: list[dict] = []

    model_config = ConfigDict(extra="allow")


class GenerationUsageResponse(BaseModel):
    """Response model for generation usage."""
    items: list[dict] = []
    generated_at: str = ""
    updated_at: str = ""

    model_config = ConfigDict(extra="allow")
