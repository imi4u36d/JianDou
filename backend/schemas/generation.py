from __future__ import annotations

from typing import Any

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field

from backend.schemas.common import _to_camel


class GenerationOptionsResponse(BaseModel):
    aspect_ratios: list = []
    image_sizes: list = []
    video_sizes: list = []
    video_durations: list = []
    text_analysis_models: list = []
    image_models: list = []
    video_models: list = []
    default_aspect_ratio: str | None = None
    default_image_size: str | None = None
    default_video_size: str | None = None
    default_video_duration_seconds: int | None = None
    default_text_analysis_model: str | None = None


class GenerationAspectRatioPreferenceRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )

    aspect_ratio: str


class GenerationAspectRatioPreferenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=_to_camel),
        populate_by_name=True,
    )

    aspect_ratio: str


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
