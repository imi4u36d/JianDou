from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.generation_service import GenerationProviderException
from backend.services.workflow_auto_pilot_executor import WorkflowAutoPilotStepExecutor
from backend.services.workflow_auto_pilot_planner import CHARACTER_SHEET_CLIP_INDEX_BASE


@pytest.mark.asyncio
async def test_executor_routes_character_sheet_generation_and_clears_label(monkeypatch) -> None:
    service = SimpleNamespace(generate_character_sheet=AsyncMock())
    labels: list[str] = []

    async def get_workflow(_workflow_id: str):
        return SimpleNamespace(text_analysis_model="text", image_model="image", video_model="video")

    async def set_current_task(_workflow_id: str, label: str) -> None:
        labels.append(label)

    monkeypatch.setattr("backend.services.workflow_auto_pilot_executor.asyncio.sleep", AsyncMock())
    executor = WorkflowAutoPilotStepExecutor(service, get_workflow, set_current_task)

    await executor.execute_step(
        {"type": "generate_keyframe", "clip_index": CHARACTER_SHEET_CLIP_INDEX_BASE + 2},
        "wf_1",
        7,
    )

    service.generate_character_sheet.assert_awaited_once_with("wf_1", 2, owner_user_id=7)
    assert labels == ["正在三视图 (角色 2)", ""]


def test_executor_classifies_only_transient_provider_errors_as_retryable() -> None:
    assert WorkflowAutoPilotStepExecutor.is_retryable_provider_error(
        GenerationProviderException("ReadTimeout while calling provider")
    )
    assert not WorkflowAutoPilotStepExecutor.is_retryable_provider_error(
        GenerationProviderException("invalid request")
    )
    assert not WorkflowAutoPilotStepExecutor.is_retryable_provider_error(ValueError("ReadTimeout"))
