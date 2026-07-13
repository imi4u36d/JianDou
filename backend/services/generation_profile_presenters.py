"""Pure legacy profile dictionaries consumed by generation run services."""

from __future__ import annotations

from typing import Any


def text_profile_dict(profile: Any, requested_model: str, user_id: int | None) -> dict[str, Any]:
    return {
        "userId": user_id,
        "requestedModel": requested_model,
        "modelName": profile.config.provider_model or requested_model,
        "provider": profile.provider,
        "endpointHost": profile.endpoint_host,
        "taskEndpointHost": "",
        "source": profile.source,
        "ready": profile.ready,
        "temperature": profile.config.temperature,
        "maxTokens": profile.config.max_tokens,
        "supportsSeed": profile.supports_seed(),
        "cameraFixed": False,
        "watermark": False,
        "supportedDurations": [],
        "pollIntervalSeconds": 5,
    }


def media_profile_dict(profile: Any, requested_model: str, user_id: int | None) -> dict[str, Any]:
    return {
        "userId": user_id,
        "requestedModel": requested_model,
        "modelName": profile.config.provider_model or requested_model,
        "provider": profile.provider,
        "endpointHost": profile.endpoint_host,
        "taskEndpointHost": profile.task_endpoint_host,
        "source": profile.source,
        "ready": profile.ready,
        "temperature": 0.3,
        "maxTokens": 4096,
        "supportsSeed": profile.supports_seed(),
        "cameraFixed": profile.capabilities.camera_fixed,
        "watermark": profile.capabilities.watermark,
        "supportedDurations": profile.supported_durations(),
        "pollIntervalSeconds": profile.capabilities.poll_interval_seconds,
    }


def stub_text_profile(requested_model: str) -> dict[str, Any]:
    return {
        "modelName": requested_model or "gpt-5.5",
        "provider": "openai",
        "endpointHost": "api.stub.openai.com",
        "taskEndpointHost": "",
        "source": "python-stub",
        "ready": True,
        "temperature": 0.3,
        "maxTokens": 4096,
        "supportsSeed": False,
        "cameraFixed": False,
        "watermark": False,
        "supportedDurations": [],
        "pollIntervalSeconds": 5,
    }


def stub_media_profile(requested_model: str, media_kind: str) -> dict[str, Any]:
    return {
        "modelName": requested_model or f"stub-{media_kind}",
        "provider": "stub",
        "endpointHost": f"api.stub.{media_kind}",
        "taskEndpointHost": f"api.stub.{media_kind}",
        "source": "python-stub",
        "ready": True,
        "temperature": 0.3,
        "maxTokens": 4096,
        "supportsSeed": True,
        "cameraFixed": False,
        "watermark": False,
        "supportedDurations": [4, 5, 6, 8, 10, 12, 15],
        "pollIntervalSeconds": 5,
    }
