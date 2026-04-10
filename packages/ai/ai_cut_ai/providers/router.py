from __future__ import annotations

from ai_cut_shared.config import ModelDefinition, Settings

from .base import ResolvedModelTarget


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve(
        self,
        model_name: str | None = None,
        *,
        capability: str | None = None,
        kind: str | None = None,
    ) -> ResolvedModelTarget:
        selected = (model_name or "").strip()
        if not selected:
            selected = self._default_for_capability(capability)
        model = self.settings.model.models.get(selected)
        if model is None:
            raise RuntimeError(f"unknown model '{selected}'")
        if capability and capability not in model.capabilities:
            raise RuntimeError(f"model '{selected}' does not support capability '{capability}'")
        if kind and model.kind != kind:
            raise RuntimeError(f"model '{selected}' is not a {kind} model")
        provider = self.settings.model.providers.get(model.provider)
        if provider is None:
            raise RuntimeError(f"provider '{model.provider}' is not configured for model '{selected}'")
        return ResolvedModelTarget(model=model, provider_key=model.provider, provider=provider)

    def resolve_fallback(self, target: ResolvedModelTarget) -> ResolvedModelTarget | None:
        fallback_model = target.fallback_model
        if not fallback_model:
            return None
        return self.resolve(fallback_model)

    def list_models(self, *, capability: str | None = None, kind: str | None = None) -> list[ModelDefinition]:
        items = list(self.settings.model.models.values())
        if capability:
            items = [item for item in items if capability in item.capabilities]
        if kind:
            items = [item for item in items if item.kind == kind]
        return items

    def _default_for_capability(self, capability: str | None) -> str:
        defaults = self.settings.model.defaults
        if capability == "planner_fusion":
            return defaults.planner_fusion
        if capability == "creative_prompt":
            return defaults.creative_prompt
        if capability == "vision_analysis":
            return defaults.vision_analysis
        if capability == "prompt_rewrite":
            return defaults.prompt_rewrite
        if capability == "image_generation":
            return defaults.image_generation
        if capability == "video_generation":
            return defaults.video_generation
        return defaults.text_analysis
