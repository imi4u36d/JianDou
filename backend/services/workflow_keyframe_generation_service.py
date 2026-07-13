"""Generate and persist workflow keyframes."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
from backend.models.workflow import BizStageWorkflow
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_keyframe_persistence import (
    GeneratedFrame,
    KeyframeTarget,
    WorkflowKeyframePersistence,
)
from backend.services.workflow_keyframe_support import find_first_frame_remote_url
from backend.services.workflow_keyframe_version_store import (
    CHARACTER_SHEET_CLIP_INDEX_BASE,
    WorkflowKeyframeVersionStore,
)
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import now_iso, random_id, trim

logger = logging.getLogger(__name__)

STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value


def _dimensions_from_aspect_ratio(aspect_ratio: str | None) -> tuple[int, int]:
    normalized = trim(aspect_ratio)
    if normalized == "16:9":
        return 1824, 1024
    if normalized == "1:1":
        return 1024, 1024
    return 1024, 1824


class WorkflowKeyframeGenerationService:
    """Own keyframe model calls, continuity rules, and persistence."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        generation_service: Callable[[], Any],
        request_builder: WorkflowGenerationRequestBuilder,
        result_parser: WorkflowGenerationResultParser,
        row_factory: WorkflowPersistenceRowFactory,
        thumbnail_resolver: Callable[[str, str], str],
    ) -> None:
        self._db = db
        self._generation_service = generation_service
        self._request_builder = request_builder
        self._result_parser = result_parser
        self._versions = WorkflowKeyframeVersionStore(db)
        self._persistence = WorkflowKeyframePersistence(
            db,
            row_factory=row_factory,
            thumbnail_resolver=thumbnail_resolver,
        )

    async def generate(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._versions.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        target = await self._versions.resolve_target(workflow, clip_index)
        version_no = await self._versions.next_version_no(workflow_id, clip_index)
        width, height = _dimensions_from_aspect_ratio(workflow.aspect_ratio)
        character_sheet_urls = (
            [] if target.is_character_sheet else await self._versions.resolve_character_sheet_urls(workflow_id)
        )
        previous_tail_frame_url = await self._versions.required_previous_tail_frame_url(
            workflow_id,
            clip_index,
            target.is_character_sheet,
            missing_message=(
                f"镜头 {clip_index} 的前一个镜头（镜头 {clip_index - 1}）"
                f"缺少尾帧远程 URL，请先确保前一个镜头的关键帧已完整生成。"
            ),
        )
        start_frame, prompt = await self._generate_start_frame(
            workflow,
            target,
            clip_index,
            width,
            height,
            character_sheet_urls,
            previous_tail_frame_url,
        )
        end_frame = None
        if not target.is_character_sheet:
            end_frame = await self._generate_end_frame(
                workflow,
                target.clip,
                clip_index,
                width,
                height,
                character_sheet_urls,
                start_frame.remote_url or start_frame.output_url,
            )
        version_id = f"kv_{random_id()[:12]}"
        self._persistence.persist_complete(
            workflow,
            target,
            clip_index,
            version_no,
            version_id,
            start_frame,
            end_frame,
            prompt,
            bool(previous_tail_frame_url),
        )
        await self._versions.mark_selected_stage_version(
            workflow_id,
            clip_index,
            version_id,
        )
        workflow.current_stage = STAGE_KEYFRAME if target.is_character_sheet else WorkflowStage.VIDEO.value
        workflow.status = WorkflowStatus.READY.value
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def generate_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._versions.require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            raise ValueError("角色设定图不支持首尾帧生成，请使用角色设定图生成接口。")

        target = await self._versions.resolve_target(workflow, clip_index)
        version_no = await self._versions.next_version_no(workflow_id, clip_index)
        width, height = _dimensions_from_aspect_ratio(workflow.aspect_ratio)
        normalized_role = trim(frame_role).lower()
        is_first = normalized_role in ("first", "start", "首帧")
        is_last = normalized_role in ("last", "end", "尾帧")
        if not is_first and not is_last:
            raise ValueError(f"不支持的 frame_role: {frame_role}，仅支持 first/last。")

        character_sheet_urls = await self._versions.resolve_character_sheet_urls(workflow_id)
        reused_start_frame_url = ""
        if is_first:
            reused_start_frame_url = await self._versions.required_previous_tail_frame_url(
                workflow_id,
                clip_index,
                target.is_character_sheet,
                missing_message=(
                    f"镜头 {clip_index} 的前一个镜头（镜头 {clip_index - 1}）"
                    f"缺少已选尾帧 URL，请先生成并选中前一个镜头的尾帧。"
                ),
            )
            if reused_start_frame_url:
                prompt = self._request_builder.keyframe_prompt(workflow, target.clip or {})
                frame = self._reused_frame(reused_start_frame_url, width, height)
            else:
                request, prompt = self._request_builder.build_keyframe_request(
                    workflow,
                    workflow_id=workflow_id,
                    clip_index=clip_index,
                    width=width,
                    height=height,
                    character=target.character,
                    clip=target.clip,
                    character_sheet_urls=character_sheet_urls or None,
                )
                frame = await self._invoke_image_generation(request, width, height)
        else:
            versions = await self._versions.list_stage_versions(workflow_id)
            start_frame_remote_url = find_first_frame_remote_url(versions, clip_index)
            if not start_frame_remote_url:
                raise ValueError("未找到该镜头的首帧远端 URL，请先生成首帧后再生成尾帧。")
            request, prompt = self._request_builder.build_end_keyframe_request(
                workflow,
                workflow_id=workflow_id,
                clip_index=clip_index,
                width=width,
                height=height,
                clip=target.clip,
                start_frame_remote_url=start_frame_remote_url,
                character_sheet_urls=character_sheet_urls or None,
            )
            frame = await self._invoke_image_generation(request, width, height)

        self._persistence.persist_single_frame(
            workflow,
            target,
            clip_index,
            version_no,
            frame_role,
            is_first,
            frame,
            prompt,
            bool(reused_start_frame_url),
        )
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def _generate_start_frame(
        self,
        workflow: BizStageWorkflow,
        target: KeyframeTarget,
        clip_index: int,
        width: int,
        height: int,
        character_sheet_urls: list[str],
        previous_tail_frame_url: str,
    ) -> tuple[GeneratedFrame, str]:
        if previous_tail_frame_url:
            logger.info("Reusing previous tail frame as start frame for clip %s", clip_index)
            return (
                self._reused_frame(previous_tail_frame_url, width, height),
                self._request_builder.keyframe_prompt(workflow, target.clip or {}),
            )
        request, prompt = self._request_builder.build_keyframe_request(
            workflow,
            workflow_id=workflow.workflow_id,
            clip_index=clip_index,
            width=width,
            height=height,
            character=target.character,
            clip=target.clip,
            character_sheet_urls=character_sheet_urls or None,
        )
        return await self._invoke_image_generation(request, width, height), prompt

    async def _generate_end_frame(
        self,
        workflow: BizStageWorkflow,
        clip: dict[str, Any] | None,
        clip_index: int,
        width: int,
        height: int,
        character_sheet_urls: list[str],
        reference_url: str,
    ) -> GeneratedFrame:
        if not reference_url:
            raise ValueError(f"镜头 {clip_index} 的首帧缺少远程 URL，无法生成尾帧。")
        for attempt in range(3):
            try:
                request, _ = self._request_builder.build_end_keyframe_request(
                    workflow,
                    workflow_id=workflow.workflow_id,
                    clip_index=clip_index,
                    width=width,
                    height=height,
                    clip=clip,
                    start_frame_remote_url=reference_url,
                    character_sheet_urls=character_sheet_urls or None,
                )
                return await self._invoke_image_generation(request, width, height)
            except Exception:
                if attempt == 2:
                    logger.exception("End frame generation failed for clip %s", clip_index)
                    raise
                delay = 2**attempt
                logger.warning("End frame generation failed for clip %s; retrying in %ds", clip_index, delay)
                await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    async def _invoke_image_generation(
        self,
        request: dict[str, Any],
        width: int,
        height: int,
    ) -> GeneratedFrame:
        generation_result = await self._generation_service().create_run(request)
        image = self._result_parser.parse_image_result(
            generation_result,
            fallback_width=width,
            fallback_height=height,
        )
        return GeneratedFrame(
            output_url=image.output_url,
            remote_url=image.remote_source_url or image.output_url,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            run_id=image.run_id,
            model_info=image.model_info,
            metadata=image.metadata,
            generation_result_id=generation_result.get("id") or image.run_id,
        )

    @staticmethod
    def _reused_frame(url: str, width: int, height: int) -> GeneratedFrame:
        return GeneratedFrame(
            output_url=url,
            remote_url=url,
            mime_type="image/png",
            width=width,
            height=height,
            model_info={},
            metadata={},
        )
