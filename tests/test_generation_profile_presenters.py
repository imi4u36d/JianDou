from __future__ import annotations

from types import SimpleNamespace

from backend.services.generation_profile_presenters import (
    media_profile_dict,
    stub_media_profile,
    stub_text_profile,
    text_profile_dict,
)


def test_text_profile_projection_preserves_runtime_contract() -> None:
    profile = SimpleNamespace(
        config=SimpleNamespace(provider_model="gpt-runtime", temperature=0.2, max_tokens=2048),
        provider="openai",
        endpoint_host="api.example.com",
        source="user",
        ready=True,
        supports_seed=lambda: True,
    )

    result = text_profile_dict(profile, "requested", 7)

    assert result["userId"] == 7
    assert result["modelName"] == "gpt-runtime"
    assert result["temperature"] == 0.2
    assert result["supportsSeed"] is True


def test_media_and_stub_profiles_have_stable_capabilities() -> None:
    profile = SimpleNamespace(
        config=SimpleNamespace(provider_model="video-runtime"),
        provider="seedance",
        endpoint_host="api.example.com",
        task_endpoint_host="tasks.example.com",
        source="catalog",
        ready=True,
        supports_seed=lambda: True,
        supported_durations=lambda: [5, 10],
        capabilities=SimpleNamespace(
            camera_fixed=True,
            watermark=False,
            poll_interval_seconds=3,
        ),
    )

    result = media_profile_dict(profile, "requested", 9)

    assert result["taskEndpointHost"] == "tasks.example.com"
    assert result["supportedDurations"] == [5, 10]
    assert result["cameraFixed"] is True
    assert stub_text_profile("")["modelName"] == "gpt-5.5"
    assert stub_media_profile("", "video")["modelName"] == "stub-video"
