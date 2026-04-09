from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .video_module import VideoGenerationModule


class ImageGenerationModule:
    """Image generation module extracted from the monolithic engine."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._video_module: VideoGenerationModule | None = None

    def bind_video_module(self, module: "VideoGenerationModule") -> None:
        self._video_module = module

    def generate(self, payload: Any):
        # Keep image/video modules cross-linked so shared strategy can evolve
        # without re-introducing a single-file god class.
        _ = self._video_module
        request_obj = self._engine._normalize_request(payload, default_kind="image")
        return self._engine._generate_media("image", request_obj)
