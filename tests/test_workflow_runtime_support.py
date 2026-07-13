from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.services.workflow_model_validator import WorkflowModelValidator
from backend.services.workflow_thumbnail_resolver import WorkflowThumbnailResolver

pytestmark = pytest.mark.service


class _Resolver:
    def __init__(self, *, video_task_base_url: str = "https://video.example/tasks") -> None:
        self.video_task_base_url = video_task_base_url
        self.calls: list[tuple[object, ...]] = []

    def resolve_text_profile(self, model: str, user_id: int):
        self.calls.append(("text", model, user_id))
        return SimpleNamespace(provider="openai", api_key="key", base_url="https://text.example/v1", ready=True)

    def resolve_media_profile(self, model: str, kind: str, user_id: int):
        self.calls.append((kind, model, user_id))
        return SimpleNamespace(
            provider="provider",
            api_key="key",
            base_url="https://media.example/v1",
            task_base_url=self.video_task_base_url if kind == "video" else "",
            ready=True,
        )


@pytest.mark.asyncio
async def test_workflow_model_validator_resolves_all_profiles_for_the_owner() -> None:
    resolver = _Resolver()
    generation_service = SimpleNamespace(_factory=SimpleNamespace(_config_resolver=resolver))

    await WorkflowModelValidator(lambda: generation_service).validate(42, "text-model", "image-model", "video-model")

    assert resolver.calls == [
        ("text", "text-model", 42),
        ("image", "image-model", 42),
        ("video", "video-model", 42),
    ]


@pytest.mark.asyncio
async def test_workflow_model_validator_requires_video_task_endpoint() -> None:
    resolver = _Resolver(video_task_base_url="")
    generation_service = SimpleNamespace(_factory=SimpleNamespace(_config_resolver=resolver))

    with pytest.raises(ValueError, match="视频模型缺少 task_base_url"):
        await WorkflowModelValidator(lambda: generation_service).validate(42, "text", "image", "video")


def test_workflow_thumbnail_resolver_trims_results_and_degrades_on_failure() -> None:
    media_service = Mock()
    media_service.ensure_media_thumbnail.return_value = "  /storage/thumb.jpg  "
    resolver = WorkflowThumbnailResolver(media_service)

    assert resolver.resolve("video", "/storage/video.mp4", ["/storage/frame.jpg"]) == "/storage/thumb.jpg"
    media_service.ensure_media_thumbnail.assert_called_once_with(
        "video", "/storage/video.mp4", ["/storage/frame.jpg"], 480
    )

    media_service.ensure_media_thumbnail.side_effect = RuntimeError("ffmpeg failed")
    assert resolver.resolve("video", "/storage/video.mp4") == ""
    assert WorkflowThumbnailResolver(None).resolve("image", "/storage/image.png") == ""
