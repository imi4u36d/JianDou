from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .image_module import ImageGenerationModule


class VideoGenerationModule:
    """Video generation module extracted from the monolithic engine."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._image_module: ImageGenerationModule | None = None

    def bind_image_module(self, module: "ImageGenerationModule") -> None:
        self._image_module = module

    def generate(self, payload: Any):
        # Cross-reference image module for shared generation policy hooks.
        _ = self._image_module
        request_obj = self._engine._normalize_request(payload, default_kind="video")
        return self._engine._generate_media("video", request_obj)
