"""Load workflow keyframe context and manage selected stage versions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage
from backend.domain.json_payloads import read_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_keyframe_persistence import KeyframeTarget
from backend.services.workflow_keyframe_support import find_keyframe_frame_url
from backend.shared import now_iso, safe_int, trim

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value


class WorkflowKeyframeVersionStore:
    """Own database reads and selection updates needed by keyframe generation."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None,
    ) -> BizStageWorkflow | None:
        filters = [BizStageWorkflow.workflow_id == workflow_id, BizStageWorkflow.is_deleted == 0]
        if owner_user_id is not None:
            filters.append(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizStageWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def resolve_target(self, workflow: BizStageWorkflow, clip_index: int) -> KeyframeTarget:
        storyboard = await self.selected_storyboard_version(workflow)
        if storyboard is None:
            raise ValueError("请先选中一个分镜版本。")
        output = read_json_object(storyboard.output_summary_json)
        script = trim(output.get("scriptMarkdown") or output.get("previewText"))
        plan = parse_workflow_storyboard_markdown(script)
        characters, clips = plan.to_view()
        visual_assets = plan.visual_assets_view()
        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            asset_index = clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE - 1
            if asset_index < 0 or asset_index >= len(visual_assets):
                raise ValueError("公共素材不存在，请重新选择分镜版本。")
            return KeyframeTarget(character=visual_assets[asset_index], clip=None)
        clip = next((item for item in clips if safe_int(item.get("clipIndex"), 0) == clip_index), None)
        if clip is None:
            raise ValueError("镜头不存在，请重新选择分镜版本。")
        return KeyframeTarget(character=None, clip=clip)

    async def list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        result = await self._db.execute(
            select(BizStageVersion)
            .where(BizStageVersion.workflow_id == workflow_id, BizStageVersion.is_deleted == 0)
            .order_by(BizStageVersion.stage_type, BizStageVersion.clip_index, BizStageVersion.version_no.desc())
        )
        return list(result.scalars().all())

    async def selected_storyboard_version(self, workflow: BizStageWorkflow) -> BizStageVersion | None:
        versions = await self.list_stage_versions(workflow.workflow_id)
        storyboards = [version for version in versions if version.stage_type == STAGE_STORYBOARD]
        selected_id = trim(workflow.selected_storyboard_version_id)
        if selected_id:
            selected = next((version for version in storyboards if version.stage_version_id == selected_id), None)
            if selected is not None:
                return selected
        return next((version for version in storyboards if version.selected == 1), storyboards[0] if storyboards else None)

    async def resolve_character_sheet_urls(self, workflow_id: str) -> list[str]:
        return await self.resolve_visual_asset_urls(workflow_id)

    async def resolve_visual_asset_urls(
        self,
        workflow_id: str,
        clip_index: int | None = None,
        workflow: BizStageWorkflow | None = None,
    ) -> list[str]:
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE,
                BizStageVersion.selected == 1,
                BizStageVersion.is_deleted == 0,
            )
        )
        matched_asset_indexes: set[int] | None = None
        if clip_index is not None and workflow is not None:
            storyboard = await self.selected_storyboard_version(workflow)
            output = read_json_object(storyboard.output_summary_json) if storyboard else {}
            plan = parse_workflow_storyboard_markdown(trim(output.get("scriptMarkdown") or output.get("previewText")))
            clip = next((item for item in plan.clips if item.clip_index == clip_index), None)
            if clip is not None:
                clip_text = str(clip.to_view())
                matched_asset_indexes = {
                    index
                    for index, asset in enumerate(plan.visual_assets, start=1)
                    if asset.name and asset.name in clip_text
                }
        urls: list[str] = []
        for version in result.scalars().all():
            asset_index = safe_int(version.clip_index, 0) - CHARACTER_SHEET_CLIP_INDEX_BASE
            if matched_asset_indexes is not None and asset_index not in matched_asset_indexes:
                continue
            output = read_json_object(version.output_summary_json)
            url = trim(output.get("remoteSourceUrl") or output.get("sheetUrl") or output.get("fileUrl"))
            if url:
                urls.append(url)
        return urls

    async def required_previous_tail_frame_url(
        self,
        workflow_id: str,
        clip_index: int,
        is_character_sheet: bool,
        *,
        missing_message: str,
    ) -> str:
        if is_character_sheet or clip_index <= 1:
            return ""
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index - 1,
                BizStageVersion.is_deleted == 0,
            )
        )
        url = find_keyframe_frame_url(list(result.scalars().all()), clip_index - 1, "last")
        if not url:
            raise ValueError(missing_message)
        return url

    async def next_version_no(self, workflow_id: str, clip_index: int) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        return safe_int(result.scalar(), 0) + 1

    async def mark_selected_stage_version(
        self,
        workflow_id: str,
        clip_index: int,
        selected_version_id: str,
    ) -> None:
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        timestamp = now_iso()
        for version in result.scalars().all():
            version.selected = 1 if version.stage_version_id == selected_version_id else 0
            version.update_time = timestamp
