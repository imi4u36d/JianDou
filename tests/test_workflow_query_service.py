from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_query_service import WorkflowQueryService


def query_service() -> tuple[WorkflowQueryService, MagicMock, MagicMock, AsyncMock]:
    db = MagicMock()
    db.execute = AsyncMock()
    mapper = MagicMock()
    refresher = AsyncMock(return_value=False)
    return WorkflowQueryService(db, view_mapper=mapper, video_refresher=refresher), db, mapper, refresher


@pytest.mark.asyncio
async def test_paginated_list_maps_summaries_and_normalizes_page_bounds() -> None:
    service, db, mapper, _refresher = query_service()
    workflow = BizStageWorkflow(workflow_id="wf-1")
    workflow_result = MagicMock()
    workflow_result.scalars.return_value.all.return_value = [workflow]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    db.execute.side_effect = [workflow_result, count_result]
    service.list_stage_versions = AsyncMock(return_value=[])  # type: ignore[method-assign]
    mapper.to_workflow_summary.return_value = {"id": "wf-1"}

    result = await service.list_workflows(
        owner_user_id=7,
        q="running",
        status="active",
        sort="updated_desc",
        offset=-5,
        limit=0,
    )

    assert result == {"items": [{"id": "wf-1"}], "total": 1, "offset": 0, "limit": 10}
    service.list_stage_versions.assert_awaited_once_with("wf-1")
    mapper.to_workflow_summary.assert_called_once_with(workflow, [])


@pytest.mark.asyncio
async def test_detail_reloads_versions_after_video_refresh() -> None:
    service, _db, mapper, refresher = query_service()
    workflow = BizStageWorkflow(workflow_id="wf-1", final_join_asset_id="asset-final")
    stale_version = BizStageVersion(stage_version_id="version-stale")
    refreshed_version = BizStageVersion(stage_version_id="version-refreshed")
    service.require_workflow = AsyncMock(return_value=workflow)  # type: ignore[method-assign]
    service.list_stage_versions = AsyncMock(  # type: ignore[method-assign]
        side_effect=[[stale_version], [refreshed_version]],
    )
    service._load_asset_map = AsyncMock(return_value={})  # type: ignore[method-assign]
    refresher.return_value = True
    mapper.to_workflow_detail.return_value = {"id": "wf-1", "refreshed": True}

    result = await service.get_workflow("wf-1", owner_user_id=7)

    assert result == {"id": "wf-1", "refreshed": True}
    refresher.assert_awaited_once_with(workflow, [stale_version])
    assert service.list_stage_versions.await_count == 2
    mapper.to_workflow_detail.assert_called_once_with(workflow, [refreshed_version], {})


@pytest.mark.asyncio
async def test_selected_storyboard_prefers_explicit_version_then_selected_flag() -> None:
    service, _db, _mapper, _refresher = query_service()
    explicit = BizStageVersion(stage_version_id="explicit", stage_type="storyboard", selected=0)
    selected = BizStageVersion(stage_version_id="selected", stage_type="storyboard", selected=1)
    workflow = BizStageWorkflow(workflow_id="wf-1", selected_storyboard_version_id="explicit")
    service.list_stage_versions = AsyncMock(return_value=[selected, explicit])  # type: ignore[method-assign]

    assert await service.selected_storyboard_version(workflow) is explicit

    workflow.selected_storyboard_version_id = ""
    assert await service.selected_storyboard_version(workflow) is selected
