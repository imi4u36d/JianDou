from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class GenerationOptionsResponse(BaseModel):
    aspect_ratios: list = []
    style_presets: list = []
    image_sizes: list = []
    video_sizes: list = []
    video_durations: list = []
    text_analysis_models: list = []
    image_models: list = []
    video_models: list = []
    default_aspect_ratio: Optional[str] = None
    default_style_preset: Optional[str] = None
    default_image_size: Optional[str] = None
    default_video_size: Optional[str] = None
    default_video_duration_seconds: Optional[int] = None
    default_text_analysis_model: Optional[str] = None
