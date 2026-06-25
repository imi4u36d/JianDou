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
    TextProviderTransport,
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
            base_url="http://ec2-3-115-6-106.ap-northeast-1.compute.amazonaws.com:3030/v1",
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


def test_openai_chat_completion_request_is_streaming() -> None:
    prepared = ChatCompletionsInvocationStrategy().prepare(
        _text_profile("gpt-5.5", responses_api=False),
        TextModelInvocation(system_prompt="system", user_prompt="user", temperature=0.15, max_tokens=2000),
    )

    assert prepared.body["model"] == "gpt-5.5"
    assert prepared.body["temperature"] == 0.15
    assert prepared.body["stream"] is True


def test_responses_request_is_streaming_when_enabled() -> None:
    prepared = ResponsesApiInvocationStrategy().prepare(
        _text_profile("gpt-5.5", responses_api=True),
        TextModelInvocation(system_prompt="system", user_prompt="user", temperature=0.15, max_tokens=2000),
    )

    assert prepared.body["model"] == "gpt-5.5"
    assert prepared.body["temperature"] == 0.15
    assert prepared.body["stream"] is True


def test_decode_responses_api_stream_extracts_text() -> None:
    raw = "\n".join([
        'data: {"type":"response.output_text.delta","delta":"你"}',
        'data: {"type":"response.output_text.delta","delta":"好"}',
        'data: {"type":"response.completed","response":{"id":"resp_1"}}',
        "data: [DONE]",
    ])

    payload = TextProviderTransport().decode_stream(raw)

    assert payload["id"] == "resp_1"
    assert payload["output_text"] == "你好"


def test_decode_chat_completion_stream_extracts_text() -> None:
    raw = "\n".join([
        'data: {"id":"chat_1","choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        "data: [DONE]",
    ])

    payload = TextProviderTransport().decode_stream(raw)

    assert payload["id"] == "chat_1"
    assert payload["output_text"] == "Hello"


def test_stream_error_message_extracts_responses_failure() -> None:
    raw = "\n".join([
        'data: {"type":"response.failed","response":{"id":"resp_1","status":"failed","error":{"code":"rate_limit_exceeded","message":"Concurrency limit exceeded"}}}',
        "data: [DONE]",
    ])
    transport = TextProviderTransport()

    payload = transport.decode_stream(raw)

    assert transport.stream_error_message(payload) == "rate_limit_exceeded: Concurrency limit exceeded"


def test_stream_error_message_extracts_chat_error_event() -> None:
    raw = "\n".join([
        'data: {"error":{"type":"rate_limit_error","message":"Concurrency limit exceeded"}}',
        "data: [DONE]",
    ])
    transport = TextProviderTransport()

    payload = transport.decode_stream(raw)

    assert transport.stream_error_message(payload) == "rate_limit_error: Concurrency limit exceeded"
