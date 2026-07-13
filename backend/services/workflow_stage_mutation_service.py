"""Workflow stage selection, rating, and deletion mutations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
from backend.domain.json_payloads import read_json_object, write_json_object
from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_keyframe_support import is_character_sheet_version, keyframe_frame_url
from backend.services.workflow_stage_mutation_policy import (
    current_stage_for_versions,
    resolve_delete_version_chain,
)
from backend.services.workflow_stage_mutation_store import WorkflowStageMutationStore
from backend.shared import now_iso, trim

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
STAGE_JOINED = WorkflowStage.JOINED.value
STATUS_READY = WorkflowStatus.READY.value
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"


class WorkflowStageMutationService:
    """Apply stage mutations while keeping workflow state consistent."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._store = WorkflowStageMutationStore(db)

    async def select_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        version = await self._store.require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None
        await self._store.mark_selected_version(workflow_id, STAGE_STORYBOARD, 0, version_id)
        workflow.selected_storyboard_version_id = version_id
        workflow.current_stage = STAGE_KEYFRAME
        workflow.status = STATUS_READY
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def adjust_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        version = await self._store.require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None
        version.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def select_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        version = await self._store.require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None:
            return None
        await self._store.mark_selected_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        workflow.current_stage = STAGE_VIDEO
        workflow.status = STATUS_READY
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        version = await self._store.require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None or version.clip_index != clip_index:
            return None
        if trim(read_json_object(version.input_summary_json).get("variantKind")) == VARIANT_KIND_CHARACTER_SHEET:
            raise ValueError("角色三视图不支持选择首帧/尾帧。")

        normalized_role = trim(frame_role).lower()
        is_first = normalized_role in ("first", "start", "首帧")
        is_last = normalized_role in ("last", "end", "尾帧")
        if not is_first and not is_last:
            raise ValueError(f"不支持的 frame_role: {frame_role}，仅支持 first/last。")
        canonical_role = "first" if is_first else "last"
        selection_key = "selectedFirstFrame" if is_first else "selectedLastFrame"
        if not keyframe_frame_url(read_json_object(version.output_summary_json), canonical_role):
            raise ValueError(f"所选版本缺少{'首帧' if is_first else '尾帧'} URL。")

        timestamp = now_iso()
        for candidate in await self._store.list_stage_versions(workflow_id):
            if candidate.stage_type != STAGE_KEYFRAME or candidate.clip_index != clip_index:
                continue
            if is_character_sheet_version(candidate):
                continue
            output = read_json_object(candidate.output_summary_json)
            if output.get(selection_key) is True or candidate.stage_version_id == version_id:
                output[selection_key] = candidate.stage_version_id == version_id
                candidate.output_summary_json = write_json_object(output)
                candidate.update_time = timestamp
        workflow.current_stage = STAGE_VIDEO
        workflow.status = STATUS_READY
        workflow.update_time = timestamp
        await self._db.commit()
        return workflow

    async def touch_character_sheet_selection(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def select_video(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        await self._store.mark_selected_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
        workflow.current_stage = STAGE_JOINED
        workflow.status = STATUS_READY
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def rate_workflow(
        self,
        workflow_id: str,
        rating: int,
        note: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        timestamp = now_iso()
        workflow.effect_rating = rating
        workflow.effect_rating_note = note
        workflow.rated_at = timestamp
        workflow.update_time = timestamp
        await self._db.commit()
        return workflow

    async def rate_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        rating: int,
        note: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        version = await self._store.require_stage_version(workflow_id, version_id, "")
        if version is None:
            return None
        timestamp = now_iso()
        version.rating = rating
        version.rating_note = note
        version.rated_at = timestamp
        version.update_time = timestamp
        if version.material_asset_id:
            asset = await self._store.find_asset(version.material_asset_id)
            if asset is not None:
                asset.user_rating = rating
                asset.rating_note = note
        await self._db.commit()
        return workflow

    async def delete_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        target = await self._store.require_stage_version(workflow_id, version_id, "")
        if target is None:
            return None
        versions = await self._store.list_stage_versions(workflow_id)
        timestamp = now_iso()
        await self._store.delete_versions(self.resolve_delete_version_chain(target, versions), timestamp)
        workflow.update_time = timestamp
        await self._db.commit()
        return workflow

    async def delete_all_stage_versions(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        stage_type: str | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._store.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        versions = await self._store.list_stage_versions(workflow_id)
        if stage_type:
            versions = [version for version in versions if version.stage_type == stage_type]
        if not versions:
            return workflow
        timestamp = now_iso()
        await self._store.delete_versions(versions, timestamp)
        workflow.update_time = timestamp
        workflow.current_stage = current_stage_for_versions(
            await self._store.list_stage_versions(workflow_id)
        )
        await self._db.commit()
        return workflow

    resolve_delete_version_chain = staticmethod(resolve_delete_version_chain)
