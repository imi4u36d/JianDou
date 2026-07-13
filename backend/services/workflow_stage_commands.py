"""Storyboard, keyframe, and video command facade methods."""

from __future__ import annotations

from typing import Any

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000


class WorkflowStageCommands:
    """Public commands that generate or select workflow stage versions."""

    async def generate_storyboard(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._storyboard_generation_service.generate(
            workflow_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.select_storyboard(
            workflow_id,
            version_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def adjust_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        prompt: str | None = None,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.adjust_storyboard(
            workflow_id,
            version_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            raise ValueError("角色设定图请使用 /character-sheets/{character_index}/generate 接口生成。")
        workflow = await self._keyframe_generation_service.generate(
            workflow_id,
            clip_index,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def generate_character_sheet(
        self,
        workflow_id: str,
        character_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        if character_index <= 0:
            raise ValueError("角色序号必须从 1 开始。")
        workflow = await self._keyframe_generation_service.generate(
            workflow_id,
            CHARACTER_SHEET_CLIP_INDEX_BASE + character_index,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def generate_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._keyframe_generation_service.generate_frame(
            workflow_id,
            clip_index,
            frame_role,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.select_keyframe(
            workflow_id,
            clip_index,
            version_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.select_keyframe_frame(
            workflow_id,
            clip_index,
            version_id,
            frame_role,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_character_sheet_asset(
        self,
        workflow_id: str,
        clip_index: int,
        asset_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.touch_character_sheet_selection(
            workflow_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def generate_video(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._video_generation_service.generate(
            workflow_id,
            clip_index,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_video(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        workflow = await self._stage_mutation_service.select_video(
            workflow_id,
            clip_index,
            version_id,
            owner_user_id=owner_user_id,
        )
        if workflow is None:
            return None
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)
