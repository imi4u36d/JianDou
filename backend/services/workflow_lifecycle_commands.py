"""Workflow lifecycle, query, rating, and cleanup command facade methods."""

from __future__ import annotations

from typing import Any


class WorkflowLifecycleCommands:
    """Public workflow commands that do not generate stage media."""

    async def create_workflow(
        self,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._lifecycle_service.create(request, owner_user_id)
        return await self.get_workflow(workflow.workflow_id, owner_user_id=owner_user_id)

    async def create_workflow_from_material(
        self,
        *,
        asset_id: str,
        owner_user_id: int,
        mode: str = "clone",
    ) -> dict[str, Any] | None:
        workflow = await self._lifecycle_service.create_from_material(
            asset_id=asset_id,
            owner_user_id=owner_user_id,
            mode=mode,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow.workflow_id, owner_user_id=owner_user_id)

    async def list_workflows(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        return await self._query_service.list_workflows(
            owner_user_id=owner_user_id,
            q=q,
            status=status,
            sort=sort,
            offset=offset,
            limit=limit,
        )

    async def get_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        return await self._query_service.get_workflow(workflow_id, owner_user_id)

    async def delete_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._lifecycle_service.delete(workflow_id, owner_user_id)
        if workflow is None:
            return None
        return {"workflowId": workflow_id, "deleted": True}

    async def update_workflow_settings(
        self,
        workflow_id: str,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._lifecycle_service.update_settings(
            workflow_id,
            request,
            owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def _update_auto_pilot_fields(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        *,
        execution_mode: str | None = None,
        auto_pilot_state: str | None = None,
        auto_pilot_next_stage: str | None = None,
        auto_pilot_error_message: str | None = None,
        auto_pilot_started_at: str | None = None,
        auto_pilot_paused_at: str | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._lifecycle_service.update_auto_pilot_fields(
            workflow_id,
            owner_user_id,
            execution_mode=execution_mode,
            auto_pilot_state=auto_pilot_state,
            auto_pilot_next_stage=auto_pilot_next_stage,
            auto_pilot_error_message=auto_pilot_error_message,
            auto_pilot_started_at=auto_pilot_started_at,
            auto_pilot_paused_at=auto_pilot_paused_at,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def rate_workflow(
        self,
        workflow_id: str,
        rating: int,
        note: str = "",
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.rate_workflow(
            workflow_id,
            rating,
            note,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def rate_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        rating: int,
        note: str = "",
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.rate_stage_version(
            workflow_id,
            version_id,
            rating,
            note,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def delete_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.delete_stage_version(
            workflow_id,
            version_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def delete_all_stage_versions(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        stage_type: str | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.delete_all_stage_versions(
            workflow_id,
            owner_user_id=owner_user_id,
            stage_type=stage_type,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)
