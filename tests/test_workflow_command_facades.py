from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.workflow_lifecycle_commands import WorkflowLifecycleCommands
from backend.services.workflow_stage_commands import (
    CHARACTER_SHEET_CLIP_INDEX_BASE,
    WorkflowStageCommands,
)

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_lifecycle_delete_returns_stable_facade_payload() -> None:
    commands = WorkflowLifecycleCommands()
    commands._lifecycle_service = SimpleNamespace(  # type: ignore[attr-defined]
        delete=AsyncMock(return_value=SimpleNamespace(workflow_id="workflow-1"))
    )

    result = await commands.delete_workflow("workflow-1", owner_user_id=7)

    commands._lifecycle_service.delete.assert_awaited_once_with("workflow-1", 7)  # type: ignore[attr-defined]
    assert result == {"workflowId": "workflow-1", "deleted": True}


@pytest.mark.asyncio
async def test_stage_generation_delegates_then_reloads_workflow() -> None:
    commands = WorkflowStageCommands()
    commands._storyboard_generation_service = SimpleNamespace(  # type: ignore[attr-defined]
        generate=AsyncMock(return_value=SimpleNamespace(workflow_id="workflow-1"))
    )
    commands.get_workflow = AsyncMock(return_value={"workflowId": "workflow-1"})  # type: ignore[attr-defined,method-assign]

    result = await commands.generate_storyboard("workflow-1", owner_user_id=7)

    commands._storyboard_generation_service.generate.assert_awaited_once_with(  # type: ignore[attr-defined]
        "workflow-1",
        owner_user_id=7,
    )
    commands.get_workflow.assert_awaited_once_with("workflow-1", owner_user_id=7)  # type: ignore[attr-defined]
    assert result == {"workflowId": "workflow-1"}


@pytest.mark.asyncio
async def test_stage_generation_keeps_character_sheet_index_guards() -> None:
    commands = WorkflowStageCommands()

    with pytest.raises(ValueError, match="角色设定图"):
        await commands.generate_keyframe("workflow-1", CHARACTER_SHEET_CLIP_INDEX_BASE)
    with pytest.raises(ValueError, match="角色序号必须从 1 开始"):
        await commands.generate_character_sheet("workflow-1", 0)


@pytest.mark.asyncio
async def test_stage_generation_supports_public_visual_asset_indexes() -> None:
    commands = WorkflowStageCommands()
    commands._keyframe_generation_service = SimpleNamespace(  # type: ignore[attr-defined]
        generate=AsyncMock(return_value=SimpleNamespace(workflow_id="workflow-1"))
    )
    commands.get_workflow = AsyncMock(return_value={"workflowId": "workflow-1"})  # type: ignore[attr-defined,method-assign]

    result = await commands.generate_visual_asset("workflow-1", 3, owner_user_id=7)

    commands._keyframe_generation_service.generate.assert_awaited_once_with(  # type: ignore[attr-defined]
        "workflow-1", CHARACTER_SHEET_CLIP_INDEX_BASE + 3, owner_user_id=7
    )
    assert result == {"workflowId": "workflow-1"}
