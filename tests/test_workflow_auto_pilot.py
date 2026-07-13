"""Tests for backend/services/workflow_auto_pilot.py — WorkflowAutoPilot engine."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.domain.enums import AutoPilotState, WorkflowStage
from backend.services.workflow_auto_pilot import (
    CHARACTER_SHEET_CLIP_INDEX_BASE,
    MAX_ITERATIONS,
    WorkflowAutoPilot,
)

pytestmark = pytest.mark.service

# ---------------------------------------------------------------------------
# Helpers — build mock workflow and version objects
# ---------------------------------------------------------------------------


def _mock_workflow(
    workflow_id: str = "wf_1",
    execution_mode: str = "manual",
    auto_pilot_state: str = AutoPilotState.IDLE.value,
    selected_storyboard_version_id: str = "",
    **kwargs: Any,
) -> MagicMock:
    """Return a MagicMock that mimics a BizStageWorkflow row."""
    wf = MagicMock()
    wf.workflow_id = workflow_id
    wf.execution_mode = execution_mode
    wf.auto_pilot_state = auto_pilot_state
    wf.auto_pilot_error_message = kwargs.get("auto_pilot_error_message", "")
    wf.auto_pilot_started_at = kwargs.get("auto_pilot_started_at", "")
    wf.auto_pilot_paused_at = kwargs.get("auto_pilot_paused_at", "")
    wf.selected_storyboard_version_id = selected_storyboard_version_id
    wf.is_deleted = 0
    return wf


def _mock_version(
    stage_type: str,
    clip_index: int = 1,
    version_no: int = 1,
    stage_version_id: str = "sv_1",
    selected: int = 0,
    material_asset_id: str = "",
    preview_url: str = "",
    input_summary_json: str = "",
) -> MagicMock:
    """Return a MagicMock that mimics a BizStageVersion row."""
    v = MagicMock()
    v.stage_type = stage_type
    v.clip_index = clip_index
    v.version_no = version_no
    v.stage_version_id = stage_version_id
    v.selected = selected
    v.material_asset_id = material_asset_id
    v.preview_url = preview_url
    v.input_summary_json = input_summary_json
    return v


def _mock_storyboard_version(
    version_no: int = 1,
    selected: int = 0,
) -> MagicMock:
    """Return a storyboard version."""
    v = _mock_version(
        stage_type=WorkflowStage.STORYBOARD.value,
        version_no=version_no,
        selected=selected,
    )
    return v


# ---------------------------------------------------------------------------
# _compute_next_steps — pure function tests (mocking _get_storyboard_plan)
# ---------------------------------------------------------------------------


class TestComputeNextSteps:
    """Tests for the pure-function step computation logic.

    _get_storyboard_plan is mocked to return predictable (characters, clips)
    tuples so we can test the actual step-selection algorithm in isolation.

    Note: _compute_next_steps returns a **list** of steps.  Single-phase
    results (storyboard, select, wait, finalize, complete) are single-element
    lists; batch phases (keyframes, videos) may return multiple elements.
    """

    def _make_pilot(self) -> WorkflowAutoPilot:
        svc = MagicMock()
        return WorkflowAutoPilot(db=MagicMock(), workflow_service=svc)

    def test_no_storyboard_generates_storyboard(self):
        pilot = self._make_pilot()
        wf = _mock_workflow()
        result = pilot._compute_next_steps(wf, [])
        assert result == [{"type": "generate_storyboard"}]

    def test_has_storyboard_no_selected_selects_first(self):
        pilot = self._make_pilot()
        wf = _mock_workflow()
        sb = _mock_storyboard_version(version_no=1)
        result = pilot._compute_next_steps(wf, [sb])
        assert result == [{"type": "select_storyboard", "version_id": "sv_1"}]

    def test_storyboard_selected_empty_script_finalizes(self):
        """Empty storyboard script -> no clips/chars -> finalize."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        # Mock _get_storyboard_plan to return empty lists
        pilot._get_storyboard_plan = MagicMock(return_value=([], []))
        result = pilot._compute_next_steps(wf, [sb])
        assert result == [{"type": "finalize"}]

    def test_missing_character_sheet_generates_keyframe(self):
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],  # 1 character
                [{"clipIndex": 1}],  # 1 clip
            )
        )
        result = pilot._compute_next_steps(wf, [sb])
        assert len(result) >= 1
        assert any(
            s["type"] == "generate_keyframe" and s["clip_index"] == CHARACTER_SHEET_CLIP_INDEX_BASE + 1 for s in result
        )

    def test_missing_clip_keyframe_generates_keyframe(self):
        """Character sheet exists but clip keyframe is missing."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}],
            )
        )
        # Character sheet exists
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf])
        assert len(result) >= 1
        assert any(s["type"] == "generate_keyframe" and s["clip_index"] == 1 for s in result)

    def test_keyframe_no_selection_generates_keyframe(self):
        """Keyframe exists but none selected -> generate more."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        clip_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=0,  # not selected
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf, clip_kf])
        assert len(result) >= 1
        assert any(s["type"] == "generate_keyframe" and s["clip_index"] == 1 for s in result)

    def test_keyframes_ready_missing_video_generates_video(self):
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        clip_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=1,
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf, clip_kf])
        assert len(result) >= 1
        assert any(s["type"] == "generate_video" and s["clip_index"] == 1 for s in result)

    def test_all_videos_ready_selects_first_video(self):
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        clip_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=1,
        )
        vid = _mock_version(
            stage_type=WorkflowStage.VIDEO.value,
            clip_index=1,
            version_no=1,
            material_asset_id="asset_1",
            preview_url="http://example.com/video.mp4",
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf, clip_kf, vid])
        assert len(result) >= 1
        assert any(s["type"] == "select_video" and s["clip_index"] == 1 for s in result)

    def test_all_stages_complete_returns_complete(self):
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        clip_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=1,
        )
        vid = _mock_version(
            stage_type=WorkflowStage.VIDEO.value,
            clip_index=1,
            version_no=1,
            material_asset_id="asset_1",
            preview_url="http://example.com/video.mp4",
            selected=1,
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf, clip_kf, vid])
        assert result == [{"type": "complete"}]

    def test_multiple_clips_batches_videos(self):
        """Should return ALL missing video steps at once."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}, {"clipIndex": 2}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        kf1 = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=1,
        )
        kf2 = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=2,
            selected=1,
        )
        # Both videos missing
        result = pilot._compute_next_steps(wf, [sb, char_kf, kf1, kf2])
        assert len(result) == 2
        assert all(s["type"] == "generate_video" for s in result)
        assert {s["clip_index"] for s in result} == {1, 2}

    def test_multiple_clips_one_video_done_batches_remaining(self):
        """Clip 1 video complete, clip 2 video missing -> batch should have only clip 2."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}],
                [{"clipIndex": 1}, {"clipIndex": 2}],
            )
        )
        char_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            selected=1,
        )
        kf1 = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=1,
        )
        kf2 = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=2,
            selected=1,
        )
        vid1 = _mock_version(
            stage_type=WorkflowStage.VIDEO.value,
            clip_index=1,
            selected=1,
            material_asset_id="asset_1",
            preview_url="http://example.com/v1.mp4",
        )
        result = pilot._compute_next_steps(wf, [sb, char_kf, kf1, kf2, vid1])
        assert len(result) == 1
        assert result[0]["type"] == "generate_video"
        assert result[0]["clip_index"] == 2

    def test_multiple_clips_selects_every_completed_video_before_finalize(self):
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [],
                [{"clipIndex": 1}, {"clipIndex": 2}],
            )
        )
        keyframes = [
            _mock_version(stage_type=WorkflowStage.KEYFRAME.value, clip_index=clip_index, selected=1)
            for clip_index in (1, 2)
        ]
        videos = [
            _mock_version(
                stage_type=WorkflowStage.VIDEO.value,
                clip_index=1,
                selected=1,
                material_asset_id="asset_1",
                preview_url="http://example.com/v1.mp4",
            ),
            _mock_version(
                stage_type=WorkflowStage.VIDEO.value,
                clip_index=2,
                stage_version_id="video_2",
                material_asset_id="asset_2",
                preview_url="http://example.com/v2.mp4",
            ),
        ]

        result = pilot._compute_next_steps(wf, [sb, *keyframes, *videos])

        assert result == [{"type": "select_video", "clip_index": 2, "version_id": "video_2"}]

    def test_multiple_characters_batched(self):
        """All missing character sheets should be batched together with any
        missing regular keyframes."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}, {"name": "Villain"}],
                [{"clipIndex": 1}],
            )
        )
        result = pilot._compute_next_steps(wf, [sb])
        # Both character sheets + 1 regular keyframe = 3
        assert len(result) == 3
        assert all(s["type"] == "generate_keyframe" for s in result)
        assert {s["clip_index"] for s in result} == {
            CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            CHARACTER_SHEET_CLIP_INDEX_BASE + 2,
            1,
        }

    def test_characters_and_clips_batched_together(self):
        """Character sheets and regular keyframes should be batched together."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [{"name": "Hero"}, {"name": "Villain"}],
                [{"clipIndex": 1}, {"clipIndex": 2}],
            )
        )
        # No keyframe versions at all
        result = pilot._compute_next_steps(wf, [sb])
        # Should include 2 character sheets + 2 regular keyframes = 4
        assert len(result) == 4
        assert all(s["type"] == "generate_keyframe" for s in result)
        clip_indexes = {s["clip_index"] for s in result}
        assert clip_indexes == {
            CHARACTER_SHEET_CLIP_INDEX_BASE + 1,
            CHARACTER_SHEET_CLIP_INDEX_BASE + 2,
            1,
            2,
        }

    def test_keyframe_selected_but_unselected_still_generated(self):
        """Keyframe exists with selected=0 -> should still be in the batch."""
        pilot = self._make_pilot()
        wf = _mock_workflow(selected_storyboard_version_id="sv_1")
        sb = _mock_storyboard_version(version_no=1, selected=1)
        pilot._get_storyboard_plan = MagicMock(
            return_value=(
                [],
                [{"clipIndex": 1}],
            )
        )
        clip_kf = _mock_version(
            stage_type=WorkflowStage.KEYFRAME.value,
            clip_index=1,
            selected=0,  # exists but not selected
        )
        result = pilot._compute_next_steps(wf, [sb, clip_kf])
        assert len(result) == 1
        assert result[0]["type"] == "generate_keyframe"
        assert result[0]["clip_index"] == 1


# ---------------------------------------------------------------------------
# _get_storyboard_plan — parser tests (limited, due to parser quirks)
# ---------------------------------------------------------------------------


class TestGetStoryboardPlan:
    def _make_pilot(self) -> WorkflowAutoPilot:
        svc = MagicMock()
        return WorkflowAutoPilot(db=MagicMock(), workflow_service=svc)

    def test_empty_script(self):
        pilot = self._make_pilot()
        sb = _mock_storyboard_version()
        chars, clips = pilot._get_storyboard_plan(sb)
        assert chars == []
        assert clips == []

    def test_characters_and_clips_from_json(self):
        """Test that the parser extracts at least 1 character and 1 clip from
        the standard markdown table format used by the storyboard generator."""
        pilot = self._make_pilot()
        script = (
            "## 角色定义\n"
            "| 名称 | 外观 |\n"
            "|------|------|\n"
            "| Hero | 勇敢的年轻战士，身穿铠甲 |\n"
            "\n"
            "## 分镜脚本\n"
            "| 序号 | 首帧 | 尾帧 | 场景 | 时长 |\n"
            "|------|------|------|------|------|\n"
            "| 1 | 英雄站在山顶 | 英雄拔出剑 | 山顶全景 | 5s |\n"
            "| 2 | 英雄冲向敌人 | 英雄挥剑 | 战场 | 8s |\n"
        )
        sb = _mock_storyboard_version()
        sb.output_summary_json = json.dumps({"scriptMarkdown": script})
        chars, clips = pilot._get_storyboard_plan(sb)
        assert len(chars) >= 1
        assert chars[0]["name"] == "Hero"
        assert len(clips) >= 2
        assert clips[0]["clipIndex"] == 1

    def test_multiple_characters_no_clips(self):
        """Multiple characters in the character table without any clips."""
        pilot = self._make_pilot()
        script = (
            "## 角色定义\n| 名称 | 外观 |\n|------|------|\n| Hero | 勇敢的年轻战士 |\n| Villain | 邪恶的黑暗法师 |\n"
        )
        sb = _mock_storyboard_version()
        sb.output_summary_json = json.dumps({"scriptMarkdown": script})
        chars, clips = pilot._get_storyboard_plan(sb)
        assert len(chars) >= 1
        assert chars[0]["name"] == "Hero"
        assert len(clips) == 0


# ---------------------------------------------------------------------------
# run() — integration with mock DB and service
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the main run loop with mocked dependencies."""

    def _make_result(self, scalar):
        """Create a SQLAlchemy-like ExecuteResult mock."""
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=scalar)
        return result

    @pytest.mark.asyncio
    async def test_run_workflow_not_found(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=self._make_result(None))
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        result = await pilot.run("wf_missing", owner_user_id=1)
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_run_already_completed(self):
        db = MagicMock()
        wf = _mock_workflow(auto_pilot_state=AutoPilotState.COMPLETED.value)
        db.execute = AsyncMock(return_value=self._make_result(wf))
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        result = await pilot.run("wf_1", owner_user_id=1)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_already_failed(self):
        db = MagicMock()
        wf = _mock_workflow(
            auto_pilot_state=AutoPilotState.FAILED.value,
            auto_pilot_error_message="previous error",
        )
        db.execute = AsyncMock(return_value=self._make_result(wf))
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        result = await pilot.run("wf_1", owner_user_id=1)
        assert result["status"] == "failed"
        assert result["error"] == "previous error"

    @pytest.mark.asyncio
    async def test_run_max_iterations(self):
        """Should stop after MAX_ITERATIONS loops."""
        db = MagicMock()
        wf = _mock_workflow()
        db.execute = AsyncMock(return_value=self._make_result(wf))
        db.commit = AsyncMock()

        svc = MagicMock()
        svc._list_stage_versions = AsyncMock(return_value=[])
        # Mock all service methods used by _execute_step as AsyncMock
        for method_name in (
            "generate_storyboard",
            "select_storyboard",
            "generate_keyframe",
            "generate_video",
            "select_video",
            "finalize_workflow",
        ):
            setattr(svc, method_name, AsyncMock())

        pilot = WorkflowAutoPilot(db=db, workflow_service=svc)
        # Make _compute_next_steps keep returning generate_storyboard
        pilot._compute_next_steps = lambda wf, versions: [{"type": "generate_storyboard"}]

        result = await pilot.run("wf_1", owner_user_id=1)
        assert result["status"] == "max_iterations"
        assert result["iterations"] == MAX_ITERATIONS


# ---------------------------------------------------------------------------
# _set_state — DB state update tests
# ---------------------------------------------------------------------------


class TestSetState:
    @pytest.mark.asyncio
    async def test_set_state_running(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        wf = _mock_workflow()
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        await pilot._set_state(wf, AutoPilotState.RUNNING)

        db.execute.assert_called()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_state_with_error(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        wf = _mock_workflow()
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        await pilot._set_state(wf, AutoPilotState.FAILED, error_message="something broke")

        db.execute.assert_called()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_state_paused(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        wf = _mock_workflow()
        pilot = WorkflowAutoPilot(db=db, workflow_service=MagicMock())
        await pilot._set_state(wf, AutoPilotState.PAUSED)

        db.execute.assert_called()
        db.commit.assert_called_once()
