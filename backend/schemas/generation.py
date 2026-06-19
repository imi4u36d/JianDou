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
