"""Text-provider orchestration with stable compatibility exports."""

from __future__ import annotations

import time
from typing import Any

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_config_profiles import ModelRuntimeProfile
from backend.services.model_invocation_config import GenerationConfigurationException
from backend.services.model_invocation_text_contracts import (
    PreparedTextModelRequest,
    TextModelInvocation,
    TextModelInvocationStrategy,
    TextModelProvider,
    TextModelResponse,
    TextModelTransportPolicy,
)
from backend.services.model_invocation_text_strategies import (
    ChatCompletionsInvocationStrategy,
    ResponsesApiInvocationStrategy,
)
from backend.services.model_invocation_text_transport import TextProviderTransport

__all__ = [
    "ChatCompletionsInvocationStrategy",
    "OpenAiCompatibleTextModelProvider",
    "PreparedTextModelRequest",
    "ResponsesApiInvocationStrategy",
    "TextModelInvocation",
    "TextModelInvocationStrategy",
    "TextModelProvider",
    "TextModelResponse",
    "TextModelTransportPolicy",
    "TextProviderTransport",
]


class OpenAiCompatibleTextModelProvider:
    """Select a request strategy and orchestrate an OpenAI-compatible call."""

    def __init__(
        self,
        transport: TextProviderTransport | None = None,
        invocation_strategies: list[TextModelInvocationStrategy] | None = None,
    ):
        self._transport = transport or TextProviderTransport()
        self._invocation_strategies = list(
            invocation_strategies
            if invocation_strategies is not None
            else [ResponsesApiInvocationStrategy(), ChatCompletionsInvocationStrategy()]
        )

    def supports(self, profile: ModelRuntimeProfile) -> bool:
        return profile is not None and bool(profile.config.provider)

    async def generate(
        self,
        profile: ModelRuntimeProfile,
        invocation: TextModelInvocation,
    ) -> TextModelResponse:
        if not profile.ready:
            raise GenerationConfigurationException("text model config missing api key or base url")
        prepared = self._prepare(profile, invocation)
        started_at = time.monotonic_ns()
        if prepared.body.get("stream"):
            response_map, http_status = await self._transport.send_streaming_json(
                prepared.endpoint,
                profile.api_key,
                prepared.body,
                profile.config.timeout_seconds,
                "text model request failed",
            )
        else:
            response = await self._transport.send_json(
                prepared.endpoint,
                profile.api_key,
                prepared.body,
                profile.config.timeout_seconds,
                "text model request failed",
            )
            response_map = self._transport.decode(response.text)
            http_status = response.status_code
        latency_ms = int((time.monotonic_ns() - started_at) / 1_000_000)
        provider_request: dict[str, Any] = {
            "method": "POST",
            "endpoint": prepared.endpoint,
            "body": prepared.body,
        }
        text = self._transport.extract_text(response_map).strip()
        if not text:
            raise GenerationProviderException(
                "text model response is empty",
                provider_request=provider_request,
                provider_response=response_map,
                http_status=http_status,
            )
        return TextModelResponse(
            text=text,
            endpoint=prepared.endpoint,
            endpoint_host=self._transport.endpoint_host(prepared.endpoint),
            latency_ms=latency_ms,
            responses_api=prepared.responses_api,
            response_id=self._transport.string_value(response_map.get("id")),
            provider_request=provider_request,
            provider_response=response_map,
            http_status=http_status,
        )

    def _prepare(
        self,
        profile: ModelRuntimeProfile,
        invocation: TextModelInvocation,
    ) -> PreparedTextModelRequest:
        tried_strategies: list[str] = []
        for strategy in self._invocation_strategies:
            tried_strategies.append(strategy.__class__.__name__)
            if strategy.supports(profile, invocation):
                return strategy.prepare(profile, invocation)
        raise GenerationProviderException(
            "no text model invocation strategy matched: " + ", ".join(tried_strategies)
        )
