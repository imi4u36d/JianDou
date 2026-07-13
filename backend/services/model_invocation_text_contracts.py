"""Stable contracts and endpoint policy for text model invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from backend.services.model_config_profiles import ModelRuntimeProfile


@dataclass
class TextModelInvocation:
    system_prompt: str = ""
    user_prompt: str = ""
    temperature: float = 0.0
    max_tokens: int = 0


@dataclass
class TextModelResponse:
    text: str = ""
    endpoint: str = ""
    endpoint_host: str = ""
    latency_ms: int = 0
    responses_api: bool = False
    response_id: str = ""
    provider_request: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@dataclass
class PreparedTextModelRequest:
    endpoint: str = ""
    body: dict[str, Any] = field(default_factory=dict)
    responses_api: bool = False


class TextModelTransportPolicy:
    @staticmethod
    def resolve_endpoint(base_url: str, use_responses_api: bool) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/responses"):
            normalized = normalized[: -len("/responses")]
        if normalized.endswith("/chat/completions"):
            normalized = normalized[: -len("/chat/completions")]
        return normalized + ("/responses" if use_responses_api else "/chat/completions")

    @staticmethod
    def supports_responses_api(profile: ModelRuntimeProfile) -> bool:
        if hasattr(profile, "supports_responses_api"):
            return profile.supports_responses_api()
        return False


@runtime_checkable
class TextModelInvocationStrategy(Protocol):
    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool: ...

    def prepare(
        self, profile: ModelRuntimeProfile, invocation: TextModelInvocation
    ) -> PreparedTextModelRequest: ...


@runtime_checkable
class TextModelProvider(Protocol):
    def supports(self, profile: ModelRuntimeProfile) -> bool: ...

    def generate(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> TextModelResponse: ...
