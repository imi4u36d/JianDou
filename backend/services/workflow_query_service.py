"""Workflow list and detail read models."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_view_mapper import WorkflowViewMapper
from backend.shared import trim

VideoRefresher = Callable[[BizStageWorkflow, list[BizStageVersion]], Awaitable[bool]]


class WorkflowQueryService:
    """Load workflow summaries and fully mapped detail views."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        view_mapper: WorkflowViewMapper,
        video_refresher: VideoRefresher,
    ) -> None:
        self._db = db
        self._view_mapper = view_mapper
        self._video_refresher = video_refresher

    async def list_workflows(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        is_paginated = offset is not None or limit is not None
        page_offset = max(0, offset or 0)
        page_limit = max(1, limit or 10)
        statement = select(BizStageWorkflow).where(BizStageWorkflow.is_deleted == 0)
        count_statement = (
            select(func.count()).select_from(BizStageWorkflow).where(BizStageWorkflow.is_deleted == 0)
        )
        if owner_user_id is not None:
            statement = statement.where(BizStageWorkflow.owner_user_id == owner_user_id)
            count_statement = count_statement.where(BizStageWorkflow.owner_user_id == owner_user_id)
        statement = self.apply_list_filters(statement, q, status)
        count_statement = self.apply_list_filters(count_statement, q, status)
        statement = self.apply_list_sort(statement, sort)
        if is_paginated:
            statement = statement.offset(page_offset).limit(page_limit)

        result = await self._db.execute(statement)
        workflows = result.scalars().all()
        items = [
            self._view_mapper.to_workflow_summary(
                workflow,
                await self.list_stage_versions(workflow.workflow_id),
            )
            for workflow in workflows
        ]
        if not is_paginated:
            return items
        count_result = await self._db.execute(count_statement)
        return {
            "items": items,
            "total": int(count_result.scalar_one() or 0),
            "offset": page_offset,
            "limit": page_limit,
        }

    async def get_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        versions = await self.list_stage_versions(workflow_id)
        if await self._video_refresher(workflow, versions):
            versions = await self.list_stage_versions(workflow_id)
        asset_map = await self._load_asset_map(versions, workflow.final_join_asset_id)
        return self._view_mapper.to_workflow_detail(workflow, versions, asset_map)

    @staticmethod
    def apply_list_filters(statement: Any, q: str | None, status: str | None):
        keyword = trim(q or "")
        if keyword:
            like = f"%{keyword}%"
            statement = statement.where(
                or_(
                    BizStageWorkflow.title.ilike(like),
                    BizStageWorkflow.status.ilike(like),
                    BizStageWorkflow.current_stage.ilike(like),
                    BizStageWorkflow.aspect_ratio.ilike(like),
                    BizStageWorkflow.execution_mode.ilike(like),
                    BizStageWorkflow.auto_pilot_state.ilike(like),
                )
            )
        normalized_status = trim(status or "").lower()
        if not normalized_status or normalized_status == "all":
            return statement
        if normalized_status == "active":
            return statement.where(
                or_(
                    BizStageWorkflow.auto_pilot_state.in_(("queued", "running", "paused")),
                    BizStageWorkflow.status.in_(("DRAFT", "READY", "RUNNING", "PAUSED")),
                )
            )
        if normalized_status == "ready":
            return statement.where(
                BizStageWorkflow.current_stage.in_(("storyboard", "keyframe", "video")),
                BizStageWorkflow.status.in_(("DRAFT", "READY", "RUNNING", "PAUSED")),
            )
        if normalized_status == "done":
            return statement.where(
                or_(
                    BizStageWorkflow.status == "COMPLETED",
                    BizStageWorkflow.current_stage == "joined",
                    BizStageWorkflow.auto_pilot_state == "completed",
                )
            )
        return statement.where(BizStageWorkflow.status == normalized_status.upper())

    @staticmethod
    def apply_list_sort(statement: Any, sort: str | None):
        normalized_sort = trim(sort or "").lower() or "created_desc"
        if normalized_sort == "updated_desc":
            return statement.order_by(BizStageWorkflow.update_time.desc(), BizStageWorkflow.id.desc())
        if normalized_sort == "status_desc":
            return statement.order_by(
                BizStageWorkflow.status.asc(),
                BizStageWorkflow.update_time.desc(),
                BizStageWorkflow.id.desc(),
            )
        return statement.order_by(BizStageWorkflow.create_time.desc(), BizStageWorkflow.id.desc())

    async def require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        filters = [
            BizStageWorkflow.workflow_id == workflow_id,
            BizStageWorkflow.is_deleted == 0,
        ]
        if owner_user_id is not None:
            filters.append(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizStageWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        result = await self._db.execute(
            select(BizStageVersion)
            .where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.is_deleted == 0,
            )
            .order_by(
                BizStageVersion.stage_type,
                BizStageVersion.clip_index,
                BizStageVersion.version_no.desc(),
            )
        )
        return list(result.scalars().all())

    async def selected_storyboard_version(self, workflow: BizStageWorkflow) -> BizStageVersion | None:
        selected_id = trim(workflow.selected_storyboard_version_id)
        storyboards = [
            version
            for version in await self.list_stage_versions(workflow.workflow_id)
            if version.stage_type == "storyboard"
        ]
        if selected_id:
            selected_by_id = next(
                (version for version in storyboards if version.stage_version_id == selected_id),
                None,
            )
            if selected_by_id is not None:
                return selected_by_id
        selected = next((version for version in storyboards if version.selected == 1), None)
        return selected or (storyboards[0] if storyboards else None)

    async def _load_asset_map(
        self,
        versions: list[BizStageVersion],
        final_join_asset_id: str | None,
    ) -> dict[str, BizMaterialAsset]:
        asset_ids = {version.material_asset_id for version in versions if version.material_asset_id}
        if final_join_asset_id:
            asset_ids.add(final_join_asset_id)
        if not asset_ids:
            return {}
        result = await self._db.execute(
            select(BizMaterialAsset).where(
                BizMaterialAsset.material_asset_id.in_(asset_ids),
                BizMaterialAsset.is_deleted == 0,
            )
        )
        return {asset.material_asset_id: asset for asset in result.scalars().all()}
