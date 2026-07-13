"""Compatibility facade for the multi-stage creative workflow lifecycle."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_keyframe_support import (
    find_first_frame_remote_url,
    find_keyframe_frame_url,
    is_character_sheet_version,
    keyframe_frame_url,
)
from backend.services.workflow_lifecycle_commands import WorkflowLifecycleCommands
from backend.services.workflow_service_composition import (
    build_workflow_service_collaborators,
    workflow_storyboard_plan,
)
from backend.services.workflow_stage_commands import (
    CHARACTER_SHEET_CLIP_INDEX_BASE as CHARACTER_SHEET_CLIP_INDEX_BASE,
)
from backend.services.workflow_stage_commands import (
    WorkflowStageCommands,
)

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
STAGE_JOINED = WorkflowStage.JOINED.value
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"


class WorkflowService(WorkflowLifecycleCommands, WorkflowStageCommands):
    """Compose focused workflow command families behind the stable service API."""

    def __init__(
        self,
        db: AsyncSession,
        generation_service: Any | None = None,
        media_service: Any | None = None,
    ) -> None:
        self.db = db
        self._generation_service = generation_service
        collaborators = build_workflow_service_collaborators(
            db,
            self._get_generation_service,
            media_service,
        )
        self._model_validator = collaborators.model_validator
        self._thumbnail_resolver = collaborators.thumbnail_resolver
        self._view_mapper = collaborators.view_mapper
        self._generation_request_builder = collaborators.generation_request_builder
        self._generation_result_parser = collaborators.generation_result_parser
        self._row_factory = collaborators.row_factory
        self._finalization_service = collaborators.finalization_service
        self._video_refresh_service = collaborators.video_refresh_service
        self._query_service = collaborators.query_service
        self._video_generation_service = collaborators.video_generation_service
        self._keyframe_generation_service = collaborators.keyframe_generation_service
        self._storyboard_generation_service = collaborators.storyboard_generation_service
        self._stage_mutation_service = collaborators.stage_mutation_service
        self._lifecycle_service = collaborators.lifecycle_service

    def _get_generation_service(self):
        if self._generation_service is None:
            raise RuntimeError("generation service not configured")
        return self._generation_service

    async def finalize_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        await self._finalization_service.finalize(workflow, versions)
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def _require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        return await self._query_service.require_workflow(workflow_id, owner_user_id)

    @staticmethod
    def _find_first_frame_remote_url(
        versions: list[BizStageVersion],
        clip_index: int,
    ) -> str:
        return find_first_frame_remote_url(versions, clip_index)

    @staticmethod
    def _is_character_sheet_version(version: BizStageVersion) -> bool:
        return is_character_sheet_version(version)

    @staticmethod
    def _keyframe_frame_url(output: dict[str, Any], frame_role: str) -> str:
        return keyframe_frame_url(output, frame_role)

    def _find_keyframe_frame_url(
        self,
        versions: list[BizStageVersion],
        clip_index: int,
        frame_role: str,
    ) -> str:
        return find_keyframe_frame_url(versions, clip_index, frame_role)

    async def _list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        return await self._query_service.list_stage_versions(workflow_id)

    async def _refresh_video_versions(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> bool:
        return await self._video_refresh_service.refresh(wf, versions)

    async def _selected_storyboard_version(self, wf: BizStageWorkflow) -> BizStageVersion | None:
        return await self._query_service.selected_storyboard_version(wf)

    def _storyboard_plan(
        self,
        version: BizStageVersion | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return workflow_storyboard_plan(version)
