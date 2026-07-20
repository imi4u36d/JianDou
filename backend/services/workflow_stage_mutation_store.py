"""Persistence operations used by workflow stage mutation commands."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.shared import now_iso


class WorkflowStageMutationStore:
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

    async def require_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        expected_stage_type: str,
    ) -> BizStageVersion | None:
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_version_id == version_id,
                BizStageVersion.is_deleted == 0,
            )
        )
        version = result.scalar_one_or_none()
        if version is None or (
            expected_stage_type and version.stage_type != expected_stage_type
        ):
            return None
        return version

    async def find_asset(self, asset_id: str, owner_user_id: int | None = None) -> BizMaterialAsset | None:
        filters = [
            BizMaterialAsset.material_asset_id == asset_id,
            BizMaterialAsset.is_deleted == 0,
        ]
        if owner_user_id is not None:
            filters.append(BizMaterialAsset.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizMaterialAsset).where(*filters))
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

    async def mark_selected_version(
        self,
        workflow_id: str,
        stage_type: str,
        clip_index: int,
        selected_version_id: str,
    ) -> None:
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == stage_type,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        timestamp = now_iso()
        for version in result.scalars().all():
            version.selected = 1 if version.stage_version_id == selected_version_id else 0
            version.update_time = timestamp

    async def delete_versions(
        self,
        versions: list[BizStageVersion],
        timestamp: str,
    ) -> None:
        for version in versions:
            version.selected = 0
            version.is_deleted = 1
            version.update_time = timestamp
            if version.material_asset_id:
                await self._db.execute(
                    update(BizMaterialAsset)
                    .where(
                        BizMaterialAsset.material_asset_id == version.material_asset_id,
                        BizMaterialAsset.is_deleted == 0,
                    )
                    .values(selected_for_next=0, is_deleted=1, update_time=timestamp)
                )
