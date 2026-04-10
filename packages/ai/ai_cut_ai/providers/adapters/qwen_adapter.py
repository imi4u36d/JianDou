from __future__ import annotations

from ai_cut_shared.config import ProviderSettings

from ..base import ProviderRequest, ProviderResponse


class QwenProviderAdapter:
    def __init__(self, provider: ProviderSettings):
        self.provider = provider
        self.provider_name = provider.name

    def generate_text(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("Qwen text adapter skeleton is not wired yet")

    def analyze_vision(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("Qwen vision adapter skeleton is not wired yet")
