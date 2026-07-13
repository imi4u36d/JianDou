from __future__ import annotations

import pytest

from backend.services.model_invocation_video import (
    AgnesVideoModelProvider,
    SeedanceVideoModelProvider,
    VideoGenerationRequest,
)

pytestmark = pytest.mark.service


def test_seedance_provider_builds_multimodal_request_body() -> None:
    request = VideoGenerationRequest(
        prompt="camera locked",
        width=1920,
        height=1080,
        duration_seconds=8,
        first_frame_url="first.png",
        last_frame_url="last.png",
        seed=42,
        camera_fixed=True,
        generate_audio=False,
    )

    body = SeedanceVideoModelProvider()._build_request_body("seedance-model", request)

    assert body["ratio"] == "16:9"
    assert body["resolution"] == "1080p"
    assert body["seed"] == 42
    assert body["generate_audio"] is False
    assert [item.get("role") for item in body["content"][1:]] == ["first_frame", "last_frame"]


def test_agnes_provider_builds_keyframes_and_valid_frame_count() -> None:
    request = VideoGenerationRequest(
        prompt="move slowly",
        width=720,
        height=1280,
        duration_seconds=10,
        first_frame_url="first.png",
        last_frame_url="last.png",
    )

    body = AgnesVideoModelProvider()._build_request_body("agnes-model", request, frame_rate=24)

    assert body["mode"] == "keyframes"
    assert body["extra_body"]["image"] == ["first.png", "last.png"]
    assert body["num_frames"] <= 441
    assert (body["num_frames"] - 1) % 8 == 0
