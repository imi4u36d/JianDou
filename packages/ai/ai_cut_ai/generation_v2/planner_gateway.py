from __future__ import annotations

from typing import Any

from ai_cut_shared.config import Settings

from ai_cut_ai.providers import ModelGateway


class PlannerModelGateway:
    """Adapter used by planners to call remote models via a single boundary."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.gateway = ModelGateway(settings)

    def invoke_vision(
        self,
        *,
        model_name: str,
        messages: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        _, result = self.gateway.invoke_vision(
            model_name=model_name,
            capability="vision_analysis",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.payload, result.raw_text

    def invoke_text_analysis(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        _, result = self.gateway.invoke_text(
            model_name=model_name,
            capability="planner_fusion",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=False,
        )
        return result.payload, result.raw_text
