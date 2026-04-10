from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ai_cut_shared.config import ModelDefinition, ProviderSettings, Settings


@dataclass(frozen=True)
class ResolvedModelTarget:
    model: ModelDefinition
    provider_key: str
    provider: ProviderSettings

    @property
    def model_name(self) -> str:
        return self.model.name

    @property
    def provider_name(self) -> str:
        return self.provider.provider

    @property
    def label(self) -> str:
        return self.model.label

    @property
    def kind(self) -> str:
        return self.model.kind

    @property
    def family(self) -> str | None:
        return self.model.family

    @property
    def description(self) -> str | None:
        return self.model.description

    @property
    def fallback_model(self) -> str | None:
        return self.model.fallback_model

    @property
    def base_url(self) -> str:
        return self.provider.base_url

    @property
    def api_key(self) -> str:
        return self.provider.api_key

    @property
    def extras(self) -> dict[str, Any]:
        return self.provider.extras


@dataclass(frozen=True)
class ProviderResult:
    payload: dict[str, Any]
    raw_text: str
    endpoint: str
    mode: str


class ProviderAdapter(Protocol):
    name: str

    def invoke_text(
        self,
        *,
        settings: Settings,
        target: ResolvedModelTarget,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        file_input_path: Path | None = None,
        file_input_name: str | None = None,
    ) -> ProviderResult:
        ...

    def invoke_vision(
        self,
        *,
        settings: Settings,
        target: ResolvedModelTarget,
        messages: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult:
        ...
