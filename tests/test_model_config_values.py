from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from backend.services.model_config_snapshot import ConfigSnapshot
from backend.services.model_config_values import (
    configured_provider_model,
    derive_base_url_from_host,
    first_valid_secret,
    host_of,
    normalize_base_url,
    parse_integer_list,
    parse_string_list,
    resolve_configured_model_section,
    resolve_text_supports_responses_api,
    resolve_watermark_default,
)


def test_base_url_helpers_normalize_provider_endpoints() -> None:
    assert derive_base_url_from_host("api.example.test") == "https://api.example.test/v1"
    assert derive_base_url_from_host("https://api.example.test/v1/") == "https://api.example.test/v1"
    assert normalize_base_url("https://api.example.test/v1/chat/completions") == "https://api.example.test/v1"
    assert normalize_base_url("https://api.example.test/v1/responses/") == "https://api.example.test/v1"
    assert host_of("https://api.example.test/v1") == "api.example.test"
    assert host_of("not a url") == ""


def test_list_and_secret_helpers_preserve_runtime_config_contracts() -> None:
    assert first_valid_secret("", "placeholder", "changeme", "sk-live") == "sk-live"
    assert parse_string_list("720x1280,720x1280,1024x1024") == ["720x1280", "1024x1024"]
    assert parse_integer_list("8,bad,8,12,0") == [8, 12]


def test_responses_api_support_uses_explicit_config_before_provider_heuristics() -> None:
    configured_false = ConfigSnapshot(
        {"model": {"providers": {"openai": {"extras": {"use_responses_api": "false"}}}}},
        "unit-test",
        [],
    )
    inferred = ConfigSnapshot({}, "unit-test", [])

    assert resolve_text_supports_responses_api(
        configured_false, "model.providers.openai", "openai", "https://api.openai.com/v1"
    ) is False
    assert resolve_text_supports_responses_api(
        inferred, "model.providers.ark", "ark", "https://ark.cn-beijing.volces.com/api/v3"
    ) is True
    assert resolve_text_supports_responses_api(
        inferred, "model.providers.local", "local", "http://localhost:11434/v1"
    ) is False


def test_model_section_and_provider_model_resolution() -> None:
    snapshot = ConfigSnapshot(
        {
            "model": {
                "models": {
                    "image-fast": {
                        "kind": "image",
                        "provider_model": "provider/image-fast-v2",
                    }
                }
            }
        },
        "unit-test",
        [],
    )

    model_name, section = resolve_configured_model_section(snapshot, "image-fast")

    assert model_name == "image-fast"
    assert section["kind"] == "image"
    assert configured_provider_model("image-fast", model_name, section) == "provider/image-fast-v2"
    assert configured_provider_model("fallback", "canonical", {}) == "canonical"


def test_watermark_defaults_are_kind_aware() -> None:
    assert resolve_watermark_default("image", "") is False
    assert resolve_watermark_default("video", "") is True
    assert resolve_watermark_default("video", "false") is False
