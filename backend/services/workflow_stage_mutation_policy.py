"""Pure stage-state and cascading-deletion policies."""

from __future__ import annotations

from backend.domain.enums import WorkflowStage
from backend.models.workflow import BizStageVersion

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
STAGE_JOINED = WorkflowStage.JOINED.value


def current_stage_for_versions(versions: list[BizStageVersion]) -> str:
    if any(version.stage_type == STAGE_VIDEO and version.selected for version in versions):
        return STAGE_JOINED
    if any(version.stage_type == STAGE_VIDEO for version in versions) or any(
        version.stage_type == STAGE_KEYFRAME and version.selected for version in versions
    ):
        return STAGE_VIDEO
    if any(version.stage_type == STAGE_KEYFRAME for version in versions) or any(
        version.stage_type == STAGE_STORYBOARD and version.selected for version in versions
    ):
        return STAGE_KEYFRAME
    return STAGE_STORYBOARD


def resolve_delete_version_chain(
    target: BizStageVersion,
    versions: list[BizStageVersion],
) -> list[BizStageVersion]:
    deleted = [target]
    if target.stage_type == STAGE_STORYBOARD:
        deleted.extend(
            version
            for version in versions
            if version.stage_type == STAGE_KEYFRAME
            and version.parent_version_id == target.stage_version_id
        )
        keyframe_ids = {
            version.stage_version_id
            for version in deleted
            if version.stage_type == STAGE_KEYFRAME
        }
        deleted.extend(
            version
            for version in versions
            if version.stage_type == STAGE_VIDEO
            and version.parent_version_id in keyframe_ids
        )
    elif target.stage_type == STAGE_KEYFRAME:
        deleted.extend(
            version
            for version in versions
            if version.stage_type == STAGE_VIDEO
            and version.parent_version_id == target.stage_version_id
        )
    return list({version.stage_version_id: version for version in deleted}.values())
