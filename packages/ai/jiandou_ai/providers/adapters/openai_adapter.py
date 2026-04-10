from __future__ import annotations

from jiandou_shared.config import ProviderSettings

from ..base import ProviderRequest, ProviderResponse


class OpenAIProviderAdapter:
    def __init__(self, provider: ProviderSettings):
        self.provider = provider

    def generate_text(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("OpenAI text adapter skeleton is not wired yet")

    def analyze_vision(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("OpenAI vision adapter skeleton is not wired yet")
