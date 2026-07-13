"""Lazy default model-provider registry for generation runs."""

from __future__ import annotations

from typing import Any

from backend.services.model_config_service import ModelRuntimePropertiesResolver

default_model_config_resolver = ModelRuntimePropertiesResolver(config_dir="./config")
_text_provider: Any | None = None
_prompt_resolver: Any | None = None
_image_providers: list[Any] = []
_video_provider: Any | None = None


def default_text_provider() -> Any:
    global _text_provider
    if _text_provider is None:
        from backend.services.model_invocation import OpenAiCompatibleTextModelProvider

        _text_provider = OpenAiCompatibleTextModelProvider()
    return _text_provider


def default_prompt_resolver() -> Any:
    global _prompt_resolver
    if _prompt_resolver is None:
        from backend.services.model_invocation import PromptTemplateResolver

        _prompt_resolver = PromptTemplateResolver()
    return _prompt_resolver


def default_image_providers() -> list[Any]:
    global _image_providers
    if not _image_providers:
        from backend.services.model_invocation import ImageProviderTransport, OpenAiImageModelProvider

        _image_providers = [OpenAiImageModelProvider(transport=ImageProviderTransport())]
    return _image_providers


def default_video_provider() -> Any:
    global _video_provider
    if _video_provider is None:
        from backend.services.model_invocation import (
            AgnesVideoModelProvider,
            CompositeVideoModelProvider,
            SeedanceVideoModelProvider,
            VideoProviderTransport,
        )

        transport = VideoProviderTransport()
        _video_provider = CompositeVideoModelProvider(
            providers=[
                SeedanceVideoModelProvider(transport=transport),
                AgnesVideoModelProvider(transport=transport),
            ]
        )
    return _video_provider
