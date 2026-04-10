from __future__ import annotations

from .base import ProviderAdapter
from .openai_compatible import OpenAICompatibleAdapter
from .openai_native import OpenAINativeAdapter


class _UnsupportedAdapter:
    def __init__(self, name: str) -> None:
        self.name = name

    def invoke_text(self, **kwargs):
        raise RuntimeError(f"provider adapter '{self.name}' does not support text invocation")

    def invoke_vision(self, **kwargs):
        raise RuntimeError(f"provider adapter '{self.name}' does not support vision invocation")


def build_provider_registry() -> dict[str, ProviderAdapter]:
    return {
        "openai_native": OpenAINativeAdapter(),
        "openai_compatible": OpenAICompatibleAdapter(),
        "aliyun_video": _UnsupportedAdapter("aliyun_video"),
        "volcengine_seed": _UnsupportedAdapter("volcengine_seed"),
    }
