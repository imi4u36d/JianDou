from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.services.workflow_service import WorkflowService

pytestmark = pytest.mark.service


class _KeyframeGenerationStub:
    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, int, int | None]] = []
        self.frame_calls: list[tuple[str, int, str, int | None]] = []

    async def generate(self, workflow_id: str, clip_index: int, owner_user_id: int | None = None) -> object:
        self.generate_calls.append((workflow_id, clip_index, owner_user_id))
        return object()

    async def generate_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> object:
        self.frame_calls.append((workflow_id, clip_index, frame_role, owner_user_id))
        return object()


async def test_workflow_facade_delegates_complete_keyframe_generation() -> None:
    service = WorkflowService(None)
    collaborator = _KeyframeGenerationStub()
    service._keyframe_generation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_1"})

    result = await service.generate_keyframe("wf_1", 2, owner_user_id=7)

    assert result == {"id": "wf_1"}
    assert collaborator.generate_calls == [("wf_1", 2, 7)]
    service.get_workflow.assert_awaited_once_with("wf_1", owner_user_id=7)


async def test_workflow_facade_maps_character_index_to_reserved_clip_index() -> None:
    service = WorkflowService(None)
    collaborator = _KeyframeGenerationStub()
    service._keyframe_generation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_1"})

    await service.generate_character_sheet("wf_1", 3, owner_user_id=8)

    assert collaborator.generate_calls == [("wf_1", 1003, 8)]


async def test_workflow_facade_delegates_single_frame_generation() -> None:
    service = WorkflowService(None)
    collaborator = _KeyframeGenerationStub()
    service._keyframe_generation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_1"})

    await service.generate_keyframe_frame("wf_1", 4, "last", owner_user_id=9)

    assert collaborator.frame_calls == [("wf_1", 4, "last", 9)]
