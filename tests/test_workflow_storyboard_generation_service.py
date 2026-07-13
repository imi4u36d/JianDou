from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.services.workflow_service import WorkflowService
from backend.services.workflow_storyboard_generation_service import storyboard_generation_error

pytestmark = pytest.mark.service


class _StoryboardGenerationStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    async def generate(self, workflow_id: str, owner_user_id: int | None = None) -> object:
        self.calls.append((workflow_id, owner_user_id))
        return object()


async def test_workflow_facade_delegates_storyboard_generation() -> None:
    service = WorkflowService(None)
    collaborator = _StoryboardGenerationStub()
    service._storyboard_generation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_story"})

    result = await service.generate_storyboard("wf_story", owner_user_id=13)

    assert result == {"id": "wf_story"}
    assert collaborator.calls == [("wf_story", 13)]
    service.get_workflow.assert_awaited_once_with("wf_story", owner_user_id=13)


def test_storyboard_generation_error_explains_missing_user_key() -> None:
    error = storyboard_generation_error(RuntimeError("missing api key or base url"))

    assert str(error) == "当前用户未设置对应模型 Key，请先在用户管理中配置 Key。"


def test_storyboard_generation_error_preserves_provider_detail() -> None:
    error = storyboard_generation_error(RuntimeError("provider unavailable"))

    assert str(error) == "分镜生成失败：provider unavailable"
