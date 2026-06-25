from __future__ import annotations

import pytest

from backend.services.model_config_service import (
    ModelRuntimeProfile,
    TextProviderCapabilities,
    TextProviderConfig,
)
from backend.services.model_invocation import (
    ChatCompletionsInvocationStrategy,
    ResponsesApiInvocationStrategy,
    TextModelInvocation,
)

pytestmark = pytest.mark.service


def _text_profile(model: str, *, responses_api: bool) -> ModelRuntimeProfile:
    return ModelRuntimeProfile(
        TextProviderConfig(
            kind="text",
            model=model,
            provider="openai",
            provider_model=model,
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            timeout_seconds=120,
            temperature=0.15,
            max_tokens=2000,
            source="unit-test",
        ),
        TextProviderCapabilities(
            supports_seed=False,
            supports_responses_api=responses_api,
        ),
    )


def test_gpt5_chat_completion_request_omits_temperature() -> None:
    prepared = ChatCompletionsInvocationStrategy().prepare(
        _text_profile("gpt-5.5", responses_api=False),
        TextModelInvocation(system_prompt="system", user_prompt="user", temperature=0.15, max_tokens=2000),
    )

    assert prepared.body["model"] == "gpt-5.5"
    assert "temperature" not in prepared.body


def test_gpt5_responses_request_omits_temperature() -> None:
    prepared = ResponsesApiInvocationStrategy().prepare(
        _text_profile("gpt-5.5", responses_api=True),
        TextModelInvocation(system_prompt="system", user_prompt="user", temperature=0.15, max_tokens=2000),
    )

    assert prepared.body["model"] == "gpt-5.5"
    assert "temperature" not in prepared.body


def test_non_gpt5_text_request_keeps_temperature() -> None:
    prepared = ChatCompletionsInvocationStrategy().prepare(
        _text_profile("gpt-4.1", responses_api=False),
        TextModelInvocation(system_prompt="system", user_prompt="user", temperature=0.15, max_tokens=2000),
    )

    assert prepared.body["temperature"] == 0.15
