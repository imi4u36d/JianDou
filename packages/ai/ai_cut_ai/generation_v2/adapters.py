from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ai_cut_ai.text_generation import (
    GenerateTextMediaRequest,
    GenerateTextMediaResponse,
    GenerateTextScriptRequest,
    GenerateTextScriptResponse,
    ProbeTextAnalysisModelRequest,
    ProbeTextAnalysisModelResponse,
    TextGenerationEngine,
)
from ai_cut_shared.schemas import VideoModelUsageResponse


class TextAnalysisAdapter(Protocol):
    def generate_script(self, payload: GenerateTextScriptRequest | dict[str, Any]) -> GenerateTextScriptResponse:
        ...

    def probe(self, payload: ProbeTextAnalysisModelRequest | dict[str, Any] | str | None = None) -> ProbeTextAnalysisModelResponse:
        ...


class ImageAdapter(Protocol):
    def generate(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        ...


class VideoAdapter(Protocol):
    def generate(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        ...


class VisionAdapter(Protocol):
    def invoke(self, *, model_name: str, body: dict[str, Any]) -> dict[str, Any]:
        ...


class UsageAdapter(Protocol):
    def get_usage(self) -> VideoModelUsageResponse:
        ...


@dataclass
class _EngineTextAnalysisAdapter:
    engine: TextGenerationEngine

    def generate_script(self, payload: GenerateTextScriptRequest | dict[str, Any]) -> GenerateTextScriptResponse:
        return self.engine.generate_text_script(payload)

    def probe(self, payload: ProbeTextAnalysisModelRequest | dict[str, Any] | str | None = None) -> ProbeTextAnalysisModelResponse:
        return self.engine.probe_text_analysis_model(payload)


@dataclass
class _EngineImageAdapter:
    engine: TextGenerationEngine

    def generate(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        return self.engine.generate_text_image(payload)


@dataclass
class _EngineVideoAdapter:
    engine: TextGenerationEngine

    def generate(self, payload: GenerateTextMediaRequest | dict[str, Any]) -> GenerateTextMediaResponse:
        return self.engine.generate_text_video(payload)


@dataclass
class _EngineVisionAdapter:
    engine: TextGenerationEngine

    def invoke(self, *, model_name: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.engine.invoke_vision_model(model_name=model_name, body=body)


class AdapterRegistry:
    """Provider adapter registry with swappable defaults."""

    def __init__(self, engine: TextGenerationEngine) -> None:
        self.engine = engine
        self._text_analysis_adapter: TextAnalysisAdapter = _EngineTextAnalysisAdapter(engine)
        self._image_adapter: ImageAdapter = _EngineImageAdapter(engine)
        self._video_adapter: VideoAdapter = _EngineVideoAdapter(engine)
        self._vision_adapter: VisionAdapter = _EngineVisionAdapter(engine)
        self._usage_adapter: UsageAdapter | None = None

    def set_text_analysis_adapter(self, adapter: TextAnalysisAdapter) -> None:
        self._text_analysis_adapter = adapter

    def set_image_adapter(self, adapter: ImageAdapter) -> None:
        self._image_adapter = adapter

    def set_video_adapter(self, adapter: VideoAdapter) -> None:
        self._video_adapter = adapter

    def set_vision_adapter(self, adapter: VisionAdapter) -> None:
        self._vision_adapter = adapter

    def set_usage_adapter(self, adapter: UsageAdapter) -> None:
        self._usage_adapter = adapter

    def text_analysis(self) -> TextAnalysisAdapter:
        return self._text_analysis_adapter

    def image(self) -> ImageAdapter:
        return self._image_adapter

    def video(self) -> VideoAdapter:
        return self._video_adapter

    def vision(self) -> VisionAdapter:
        return self._vision_adapter

    def usage(self) -> UsageAdapter | None:
        return self._usage_adapter
