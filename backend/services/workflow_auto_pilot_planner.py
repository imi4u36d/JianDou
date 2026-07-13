"""Pure next-step planning for workflow auto-pilot execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.domain.enums import WorkflowStage
from backend.domain.json_payloads import read_json_object
from backend.shared import safe_int, trim

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
PENDING_VIDEO_STATUSES = frozenset({"RUNNING", "SUBMITTED", "PENDING", "PROCESSING", ""})


class WorkflowAutoPilotPlanner:
    """Determines the next executable workflow steps without mutating state."""

    def compute_next_steps(
        self,
        workflow: Any,
        versions: list[Any],
        storyboard_plan_loader: Callable[[Any], tuple[list[dict[str, Any]], list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        storyboard_versions = [v for v in versions if v.stage_type == WorkflowStage.STORYBOARD.value]
        keyframe_versions = [v for v in versions if v.stage_type == WorkflowStage.KEYFRAME.value]
        video_versions = [v for v in versions if v.stage_type == WorkflowStage.VIDEO.value]

        if not storyboard_versions:
            return [{"type": "generate_storyboard"}]

        selected_storyboard_id = trim(workflow.selected_storyboard_version_id)
        has_selected = selected_storyboard_id and any(
            version.stage_version_id == selected_storyboard_id for version in storyboard_versions
        )
        if not has_selected:
            first_version = min(storyboard_versions, key=lambda version: safe_int(version.version_no, 0))
            return [{"type": "select_storyboard", "version_id": first_version.stage_version_id}]

        selected_storyboard = next(
            (version for version in storyboard_versions if version.stage_version_id == selected_storyboard_id),
            None,
        )
        if selected_storyboard is None:
            selected_storyboard = next((version for version in storyboard_versions if version.selected == 1), None)
        if selected_storyboard is None:
            selected_storyboard = storyboard_versions[0]

        characters, clips = storyboard_plan_loader(selected_storyboard)
        clip_indexes = [safe_int(clip.get("clipIndex"), 0) for clip in clips]

        keyframe_steps = self.missing_keyframe_steps(characters, clip_indexes, keyframe_versions)
        if keyframe_steps:
            return keyframe_steps

        video_steps, pending_clip_indexes = self.video_generation_steps(clip_indexes, video_versions)
        if pending_clip_indexes and not video_steps:
            return [{"type": "wait", "pending_clip_indexes": pending_clip_indexes}]
        if video_steps:
            return video_steps

        return self.next_completed_video_step(workflow, clip_indexes, video_versions)

    @staticmethod
    def missing_keyframe_steps(
        characters: list[dict[str, Any]], clip_indexes: list[int], keyframe_versions: list[Any]
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        existing_character_sheets = {
            version.clip_index
            for version in keyframe_versions
            if version.clip_index > CHARACTER_SHEET_CLIP_INDEX_BASE
        }
        for character_index, _character in enumerate(characters, start=1):
            clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + character_index
            if clip_index not in existing_character_sheets:
                steps.append({"type": "generate_keyframe", "clip_index": clip_index})

        for clip_index in sorted(index for index in clip_indexes if index != 0):
            versions_for_clip = [
                version
                for version in keyframe_versions
                if version.clip_index == clip_index
                and trim(read_json_object(version.input_summary_json).get("variantKind", "")) != "character_sheet"
            ]
            if not any(version.selected == 1 for version in versions_for_clip):
                steps.append({"type": "generate_keyframe", "clip_index": clip_index})
        return steps

    @staticmethod
    def video_generation_steps(
        clip_indexes: list[int], video_versions: list[Any]
    ) -> tuple[list[dict[str, Any]], list[int]]:
        steps: list[dict[str, Any]] = []
        pending_clip_indexes: list[int] = []
        for clip_index in sorted(index for index in clip_indexes if index != 0):
            versions_for_clip = [version for version in video_versions if version.clip_index == clip_index]
            if any(trim(version.material_asset_id) and trim(version.preview_url) for version in versions_for_clip):
                continue
            if any(trim(version.status).upper() in PENDING_VIDEO_STATUSES for version in versions_for_clip):
                pending_clip_indexes.append(clip_index)
                continue
            steps.append({"type": "generate_video", "clip_index": clip_index})
        return steps, pending_clip_indexes

    @staticmethod
    def next_completed_video_step(
        workflow: Any, clip_indexes: list[int], video_versions: list[Any]
    ) -> list[dict[str, Any]]:
        expected_clip_indexes = sorted(index for index in clip_indexes if index != 0)
        if not expected_clip_indexes:
            return [{"type": "finalize"}]

        selected_clip_indexes = {
            version.clip_index
            for version in video_versions
            if version.selected == 1 and trim(version.preview_url)
        }
        for clip_index in expected_clip_indexes:
            if clip_index in selected_clip_indexes:
                continue
            completed_versions = [
                version
                for version in video_versions
                if version.clip_index == clip_index
                and trim(version.material_asset_id)
                and trim(version.preview_url)
            ]
            if completed_versions:
                first_version = min(completed_versions, key=lambda version: safe_int(version.version_no, 0))
                return [{
                    "type": "select_video",
                    "clip_index": clip_index,
                    "version_id": first_version.stage_version_id,
                }]

        if len(selected_clip_indexes) < len(expected_clip_indexes):
            return [{"type": "wait", "pending_clip_indexes": expected_clip_indexes}]
        if not trim(workflow.final_join_asset_id):
            return [{"type": "finalize"}]
        return [{"type": "complete"}]
