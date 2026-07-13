from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.models.workflow import BizStageVersion
from backend.services.workflow_service import WorkflowService
from backend.services.workflow_stage_mutation_policy import current_stage_for_versions
from backend.services.workflow_stage_mutation_service import WorkflowStageMutationService
from backend.services.workflow_stage_mutation_store import WorkflowStageMutationStore

pytestmark = pytest.mark.service


def test_stage_mutation_service_composes_persistence_store() -> None:
    service = WorkflowStageMutationService(AsyncMock())

    assert isinstance(service._store, WorkflowStageMutationStore)


class _StageMutationStub:
    def __init__(self) -> None:
        self.frame_calls: list[tuple[str, int, str, str, int | None]] = []
        self.delete_calls: list[tuple[str, int | None, str | None]] = []

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> object:
        self.frame_calls.append((workflow_id, clip_index, version_id, frame_role, owner_user_id))
        return object()

    async def delete_all_stage_versions(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        stage_type: str | None = None,
    ) -> object:
        self.delete_calls.append((workflow_id, owner_user_id, stage_type))
        return object()


async def test_workflow_facade_delegates_frame_selection() -> None:
    service = WorkflowService(None)
    collaborator = _StageMutationStub()
    service._stage_mutation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_stage"})

    result = await service.select_keyframe_frame("wf_stage", 2, "kv_2", "last", owner_user_id=14)

    assert result == {"id": "wf_stage"}
    assert collaborator.frame_calls == [("wf_stage", 2, "kv_2", "last", 14)]


async def test_workflow_facade_delegates_filtered_delete_all() -> None:
    service = WorkflowService(None)
    collaborator = _StageMutationStub()
    service._stage_mutation_service = collaborator
    service.get_workflow = AsyncMock(return_value={"id": "wf_stage"})

    await service.delete_all_stage_versions("wf_stage", owner_user_id=15, stage_type="video")

    assert collaborator.delete_calls == [("wf_stage", 15, "video")]


def test_storyboard_delete_chain_includes_linked_keyframe_and_video() -> None:
    storyboard = BizStageVersion(
        stage_version_id="sv_1",
        workflow_id="wf_stage",
        stage_type="storyboard",
        clip_index=0,
        parent_version_id="",
    )
    keyframe = BizStageVersion(
        stage_version_id="kv_1",
        workflow_id="wf_stage",
        stage_type="keyframe",
        clip_index=1,
        parent_version_id="sv_1",
    )
    video = BizStageVersion(
        stage_version_id="vv_1",
        workflow_id="wf_stage",
        stage_type="video",
        clip_index=1,
        parent_version_id="kv_1",
    )
    unrelated = BizStageVersion(
        stage_version_id="kv_other",
        workflow_id="wf_stage",
        stage_type="keyframe",
        clip_index=2,
        parent_version_id="sv_other",
    )

    result = WorkflowStageMutationService.resolve_delete_version_chain(
        storyboard,
        [storyboard, keyframe, video, unrelated],
    )

    assert [version.stage_version_id for version in result] == ["sv_1", "kv_1", "vv_1"]


def test_current_stage_policy_tracks_furthest_selected_output() -> None:
    storyboard = BizStageVersion(stage_type="storyboard", selected=1)
    keyframe = BizStageVersion(stage_type="keyframe", selected=0)
    video = BizStageVersion(stage_type="video", selected=0)

    assert current_stage_for_versions([]) == "storyboard"
    assert current_stage_for_versions([storyboard]) == "keyframe"
    assert current_stage_for_versions([storyboard, keyframe]) == "keyframe"
    keyframe.selected = 1
    assert current_stage_for_versions([storyboard, keyframe]) == "video"
    assert current_stage_for_versions([storyboard, keyframe, video]) == "video"
    video.selected = 1
    assert current_stage_for_versions([storyboard, keyframe, video]) == "joined"
