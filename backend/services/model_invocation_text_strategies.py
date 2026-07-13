"""Request preparation strategies for OpenAI-compatible text APIs."""

from __future__ import annotations

from typing import Any

from backend.services.model_config_profiles import ModelRuntimeProfile
from backend.services.model_invocation_text_contracts import (
    PreparedTextModelRequest,
    TextModelInvocation,
    TextModelTransportPolicy,
)


class ChatCompletionsInvocationStrategy:
    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool:
        return True

    def prepare(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> PreparedTextModelRequest:
        body: dict[str, Any] = {
            "model": profile.config.provider_model,
            "messages": [
                {"role": "system", "content": invocation.system_prompt},
                {"role": "user", "content": invocation.user_prompt},
            ],
            "max_tokens": invocation.max_tokens,
            "stream": True,
            "temperature": invocation.temperature,
        }
        return PreparedTextModelRequest(
            endpoint=TextModelTransportPolicy.resolve_endpoint(profile.base_url, False),
            body=body,
            responses_api=False,
        )


class ResponsesApiInvocationStrategy:
    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool:
        return TextModelTransportPolicy.supports_responses_api(profile)

    def prepare(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> PreparedTextModelRequest:
        body: dict[str, Any] = {
            "model": profile.config.provider_model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": invocation.system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": invocation.user_prompt}]},
            ],
            "max_output_tokens": invocation.max_tokens,
            "stream": True,
            "temperature": invocation.temperature,
        }
        return PreparedTextModelRequest(
            endpoint=TextModelTransportPolicy.resolve_endpoint(profile.base_url, True),
            body=body,
            responses_api=True,
        )
