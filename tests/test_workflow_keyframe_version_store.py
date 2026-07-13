from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from backend.services.workflow_keyframe_version_store import WorkflowKeyframeVersionStore


async def test_selected_storyboard_prefers_workflow_selection() -> None:
    store = WorkflowKeyframeVersionStore(None)  # type: ignore[arg-type]
    fallback = SimpleNamespace(stage_type="storyboard", stage_version_id="v1", selected=1)
    selected = SimpleNamespace(stage_type="storyboard", stage_version_id="v2", selected=0)
    store.list_stage_versions = AsyncMock(return_value=[fallback, selected])  # type: ignore[method-assign]

    result = await store.selected_storyboard_version(
        SimpleNamespace(workflow_id="wf-1", selected_storyboard_version_id="v2")
    )

    assert result is selected


async def test_previous_tail_lookup_skips_first_clip_without_query() -> None:
    db = SimpleNamespace(execute=AsyncMock())
    store = WorkflowKeyframeVersionStore(db)

    result = await store.required_previous_tail_frame_url(
        "wf-1",
        1,
        False,
        missing_message="missing",
    )

    assert result == ""
    db.execute.assert_not_awaited()


async def test_next_version_number_uses_persisted_count() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar=lambda: 2)),
    )
    store = WorkflowKeyframeVersionStore(db)

    assert await store.next_version_no("wf-1", 3) == 3
    db.execute.assert_awaited_once()
