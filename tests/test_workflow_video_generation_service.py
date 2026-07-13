from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.services.workflow_service import WorkflowService
from backend.services.workflow_video_generation_service import (
    dimensions_from_size,
    video_frame_model_input,
)

pytestmark = pytest.mark.service


class _VideoGenerationStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int | None]] = []

    async def generate(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> object:
        self.calls.append((workflow_id, clip_index, owner_user_id))
        return object()


async def test_workflow_facade_delegates_video_generation() -> None:
    service = WorkflowService(None)
    collaborator = _VideoGenerationStub()
    service._video_generation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_video"})

    result = await service.generate_video("wf_video", 3, owner_user_id=12)

    assert result == {"id": "wf_video"}
    assert collaborator.calls == [("wf_video", 3, 12)]
    service.get_workflow.assert_awaited_once_with("wf_video", owner_user_id=12)


@pytest.mark.parametrize(
    ("value", "fallback", "expected"),
    [
        ("1920x1080", None, (1920, 1080)),
        ("720*1280", None, (720, 1280)),
        ("unknown", "16:9", (1824, 1024)),
        (None, "9:16", (1024, 1824)),
    ],
)
def test_dimensions_from_size(value: str | None, fallback: str | None, expected: tuple[int, int]) -> None:
    assert dimensions_from_size(value, fallback) == expected


def test_video_frame_model_input_only_accepts_remote_urls() -> None:
    assert video_frame_model_input("https://cdn.example/frame.png") == "https://cdn.example/frame.png"
    assert video_frame_model_input("/storage/frame.png") == ""
