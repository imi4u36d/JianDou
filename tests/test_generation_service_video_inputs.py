from __future__ import annotations

import pytest

from backend.services.generation_service import GenerationRunFactory

pytestmark = pytest.mark.service


class _VideoFrameSupport:
    def image_data_uri_from_public_url(self, public_url: str) -> str:
        assert public_url == "/storage/tasks/task_1/running/clip1-first.png"
        return "data:image/png;base64,abc"

    def build_externally_accessible_url(self, public_url: str) -> str:
        return f"https://cdn.example.test{public_url}"


def test_resolve_video_frame_input_converts_local_storage_image_to_data_uri() -> None:
    factory = GenerationRunFactory(support=_VideoFrameSupport())

    resolved = factory._resolve_video_frame_input(
        "/storage/tasks/task_1/running/clip1-first.png",
        "firstFrameUrl",
    )

    assert resolved == "data:image/png;base64,abc"
