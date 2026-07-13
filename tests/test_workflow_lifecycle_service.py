from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.domain.enums import AutoPilotState, WorkflowStatus
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_lifecycle_service import (
    WorkflowLifecycleService,
    aspect_ratio_from_asset,
    duration_bounds,
    normalize_duration_mode,
)


def lifecycle_service() -> tuple[WorkflowLifecycleService, MagicMock, AsyncMock]:
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    validator = AsyncMock()
    return WorkflowLifecycleService(db, model_validator=validator), db, validator


def test_duration_defaults_and_manual_bounds_are_normalized() -> None:
    assert normalize_duration_mode(None, None, None) == "auto"
    assert duration_bounds({}, "auto") == (5, 12)
    assert normalize_duration_mode(None, 8, 3) == "manual"
    assert duration_bounds({"minDurationSeconds": 8, "maxDurationSeconds": 3}, "manual") == (8, 8)


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [(1024, 1024, "1:1"), (1920, 1080, "16:9"), (1080, 1920, "9:16"), (0, 0, "9:16")],
)
def test_aspect_ratio_from_material_dimensions(width: int, height: int, expected: str) -> None:
    asset = BizMaterialAsset(width=width, height=height)

    assert aspect_ratio_from_asset(asset) == expected


@pytest.mark.asyncio
async def test_create_normalizes_defaults_and_validates_models() -> None:
    service, db, validator = lifecycle_service()

    workflow = await service.create(
        {
            "title": "测试工作流",
            "aspectRatio": "16:9",
            "textAnalysisModel": "text-model",
            "imageModel": "image-model",
            "videoModel": "video-model",
            "executionMode": "unsupported",
        },
        owner_user_id=42,
    )

    validator.assert_awaited_once_with(42, "text-model", "image-model", "video-model")
    db.add.assert_called_once_with(workflow)
    db.commit.assert_awaited_once()
    assert workflow.execution_mode == "manual"
    assert workflow.duration_mode == "auto"
    assert workflow.min_duration_seconds == 5
    assert workflow.max_duration_seconds == 12
    assert workflow.video_size == "1280*720"
    assert workflow.status == WorkflowStatus.DRAFT.value


@pytest.mark.asyncio
async def test_requeue_clears_stale_auto_pilot_state() -> None:
    service, db, _validator = lifecycle_service()
    workflow = BizStageWorkflow(
        workflow_id="wf-1",
        owner_user_id=7,
        status=WorkflowStatus.FAILED.value,
        auto_pilot_state=AutoPilotState.FAILED.value,
        auto_pilot_error_message="previous error",
        auto_pilot_current_task="rendering clip 2",
    )
    service._require_workflow = AsyncMock(return_value=workflow)  # type: ignore[method-assign]

    result = await service.update_auto_pilot_fields(
        "wf-1",
        owner_user_id=7,
        auto_pilot_state=AutoPilotState.QUEUED.value,
        auto_pilot_next_stage="keyframe",
    )

    assert result is workflow
    assert workflow.status == WorkflowStatus.READY.value
    assert workflow.auto_pilot_state == AutoPilotState.QUEUED.value
    assert workflow.auto_pilot_error_message == ""
    assert workflow.auto_pilot_current_task == ""
    assert workflow.auto_pilot_next_stage == "keyframe"
    db.commit.assert_awaited_once()
