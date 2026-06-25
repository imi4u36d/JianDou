from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
from backend.domain.generation_run import GenerationModelKinds
from backend.services.generation_payloads import (
    append_negative_prompt,
    build_media_model_info,
    build_model_info,
    build_negative_prompt,
    build_script_adjust_user_prompt,
    build_script_user_prompt,
    infer_camera_fixed,
)


def test_append_negative_prompt_handles_blank_and_non_blank_prompts() -> None:
    assert append_negative_prompt("", "no blur") == "写实影视风格。负面约束：no blur"
    assert append_negative_prompt(" main prompt ", "no blur") == "main prompt\n负面约束：no blur"


def test_infer_camera_fixed_detects_fixed_camera_keywords() -> None:
    assert infer_camera_fixed("固定镜头，人物走入画面", fallback=False) is True
    assert infer_camera_fixed("鱼眼监控视角，走廊", fallback=False) is True
    assert infer_camera_fixed("handheld movement", fallback=True) is True
    assert infer_camera_fixed("", fallback=False) is False


def test_build_model_info_prefers_response_endpoint_host() -> None:
    info = build_model_info(
        {"provider": "openai", "modelName": "gpt-x", "endpointHost": "config-host", "source": "config.yml"},
        "requested-gpt",
        "script",
        {"endpointHost": "response-host"},
        "source-tag",
    )

    assert info == {
        "provider": "openai",
        "modelName": "gpt-x",
        "providerModel": "gpt-x",
        "requestedModel": "requested-gpt",
        "resolvedModel": "gpt-x",
        "textAnalysisModel": "gpt-x",
        "mediaKind": "script",
        "endpointHost": "response-host",
        "configSource": "config.yml",
        "generationSource": "source-tag",
    }


def test_build_media_model_info_includes_optional_rewrite_and_vision_models() -> None:
    info = build_media_model_info(
        {"provider": "text-provider", "modelName": "text-model", "endpointHost": "text-host"},
        {"provider": "rewrite-provider", "modelName": "rewrite-model", "endpointHost": "rewrite-config-host"},
        {"provider": "vision-provider", "modelName": "vision-model", "endpointHost": "vision-config-host"},
        {"provider": "media-provider", "source": "config.yml"},
        "requested-media",
        GenerationModelKinds.VIDEO,
        {"endpointHost": "rewrite-response-host"},
        {"endpointHost": "vision-response-host"},
        "resolved-video",
        "media-host",
        "task-host",
        "source-tag",
    )

    assert info["provider"] == "media-provider"
    assert info["modelName"] == "resolved-video"
    assert info["textAnalysisModel"] == "text-model"
    assert info["promptRewriteEndpointHost"] == "rewrite-response-host"
    assert info["visionAnalysisEndpointHost"] == "vision-response-host"
    assert info["taskEndpointHost"] == "task-host"
    assert info["generationSource"] == "source-tag"


def test_script_prompt_builders_preserve_existing_text_shape() -> None:
    user_prompt = build_script_user_prompt("source text", "noir")
    adjust_prompt = build_script_adjust_user_prompt("source text", "noir", "script md", "make it shorter")

    assert "source text" in user_prompt
    assert "noir" in user_prompt
    assert "system prompt" in user_prompt
    assert "source text" in adjust_prompt
    assert "noir" in adjust_prompt
    assert "make it shorter" in adjust_prompt
    assert adjust_prompt.endswith("script md")


def test_build_negative_prompt_keeps_current_placeholder_contract() -> None:
    assert build_negative_prompt(GenerationModelKinds.IMAGE) == " "
    assert build_negative_prompt(GenerationModelKinds.VIDEO) == " "
