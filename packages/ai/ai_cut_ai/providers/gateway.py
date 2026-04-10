from __future__ import annotations

from pathlib import Path

from ai_cut_shared.config import Settings

from .base import ProviderResult, ResolvedModelTarget
from .registry import build_provider_registry
from .router import ModelRouter


class ModelGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.router = ModelRouter(settings)
        self.registry = build_provider_registry()

    def invoke_text(
        self,
        *,
        model_name: str | None = None,
        capability: str = "text_analysis",
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        file_input_path: Path | None = None,
        file_input_name: str | None = None,
    ) -> tuple[ResolvedModelTarget, ProviderResult]:
        target = self.router.resolve(model_name, capability=capability, kind="text")
        adapter = self._adapter_for(target)
        result = adapter.invoke_text(
            settings=self.settings,
            target=target,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            file_input_path=file_input_path,
            file_input_name=file_input_name,
        )
        return target, result

    def invoke_vision(
        self,
        *,
        model_name: str | None = None,
        capability: str = "vision_analysis",
        messages: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[ResolvedModelTarget, ProviderResult]:
        target = self.router.resolve(model_name, capability=capability, kind="vision")
        adapter = self._adapter_for(target)
        result = adapter.invoke_vision(
            settings=self.settings,
            target=target,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return target, result

    def _adapter_for(self, target: ResolvedModelTarget):
        adapter_name = str(target.extras.get("adapter") or target.provider_name).strip()
        adapter = self.registry.get(adapter_name)
        if adapter is None:
            raise RuntimeError(f"no provider adapter registered for '{adapter_name}'")
        return adapter
