"""Generate and persist workflow clip videos."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
from backend.domain.json_payloads import read_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder
from backend.services.workflow_generation_result_parser import ParsedVideoResult, WorkflowGenerationResultParser
from backend.services.workflow_keyframe_support import find_keyframe_frame_url, is_character_sheet_version
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import now_iso, random_id, safe_int, trim

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value


def dimensions_from_aspect_ratio(aspect_ratio: str | None) -> tuple[int, int]:
    normalized = trim(aspect_ratio)
    if normalized == "16:9":
        return 1824, 1024
    if normalized == "1:1":
        return 1024, 1024
    return 1024, 1824


def dimensions_from_size(
    value: str | None,
    fallback_aspect_ratio: str | None = None,
) -> tuple[int, int]:
    normalized = trim(value).lower().replace("x", "*")
    match = re.search(r"(\d{3,5})\s*\*\s*(\d{3,5})", normalized)
    if match:
        return safe_int(match.group(1), 0), safe_int(match.group(2), 0)
    if "1280" in normalized and "720" in normalized:
        return 1280, 720
    if "720" in normalized and "1280" in normalized:
        return 720, 1280
    return dimensions_from_aspect_ratio(fallback_aspect_ratio)


def video_frame_model_input(public_url: str) -> str:
    normalized = trim(public_url)
    return normalized if normalized.startswith(("http://", "https://")) else ""


class WorkflowVideoGenerationService:
    """Own video generation context, model invocation, and persistence."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        generation_service: Callable[[], Any],
        request_builder: WorkflowGenerationRequestBuilder,
        result_parser: WorkflowGenerationResultParser,
        row_factory: WorkflowPersistenceRowFactory,
        thumbnail_resolver: Callable[[str, str, list[str] | None], str],
    ) -> None:
        self._db = db
        self._generation_service = generation_service
        self._request_builder = request_builder
        self._result_parser = result_parser
        self._row_factory = row_factory
        self._thumbnail_resolver = thumbnail_resolver

    async def generate(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        clip = await self._require_storyboard_clip(workflow, clip_index)
        versions = await self._list_stage_versions(workflow_id)
        keyframe_versions = [
            version
            for version in versions
            if version.stage_type == STAGE_KEYFRAME
            and version.clip_index == clip_index
            and not is_character_sheet_version(version)
        ]
        if not keyframe_versions:
            raise ValueError("请先为该镜头生成并选中关键帧。")

        first_frame_url = find_keyframe_frame_url(keyframe_versions, clip_index, "first")
        last_frame_url = find_keyframe_frame_url(keyframe_versions, clip_index, "last")
        if not first_frame_url:
            raise ValueError("关键帧缺少远端首帧图片 URL，无法生成视频。")
        model_first_frame_url = video_frame_model_input(first_frame_url)
        model_last_frame_url = video_frame_model_input(last_frame_url) if last_frame_url else ""
        if not model_first_frame_url:
            raise ValueError("关键帧远端首帧图片 URL 不是视频模型可访问的地址，无法生成视频。")

        version_no = await self._next_version_no(workflow_id, clip_index)
        width, height = dimensions_from_size(workflow.video_size, workflow.aspect_ratio)
        duration_seconds = safe_int(clip.get("targetDurationSeconds"), workflow.min_duration_seconds or 8)
        duration_seconds = max(1, min(duration_seconds, workflow.max_duration_seconds or duration_seconds))
        request, prompt = self._request_builder.build_video_request(
            workflow,
            workflow_id=workflow_id,
            clip_index=clip_index,
            clip=clip,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            first_frame_url=model_first_frame_url,
            last_frame_url=model_last_frame_url,
        )
        generation_result = await self._generation_service().create_run(request)
        video = self._result_parser.parse_video_result(
            generation_result,
            fallback_preview_url=first_frame_url,
            fallback_width=width,
            fallback_height=height,
            fallback_duration_seconds=duration_seconds,
        )
        version_id = f"vv_{random_id()[:12]}"
        asset_id = self._persist_video_asset(
            workflow,
            clip,
            clip_index,
            version_no,
            video,
            prompt,
            first_frame_url,
            last_frame_url,
        )
        selected_keyframe = next((version for version in keyframe_versions if version.selected == 1), None)
        stage_version = self._row_factory.create_stage_version(
            wf=workflow,
            stage_version_id=version_id,
            stage_type=STAGE_VIDEO,
            clip_index=clip_index,
            version_no=version_no,
            title=f"镜头 {clip_index} 视频 {version_no}",
            status="COMPLETED" if video.output_url else video.status,
            selected=1 if video.output_url else 0,
            parent_version_id=selected_keyframe.stage_version_id if selected_keyframe else "",
            material_asset_id=asset_id,
            preview_url=video.preview_url,
            download_url=video.output_url,
            input_summary={
                "clipIndex": clip_index,
                "prompt": prompt,
                "firstFrameUrl": first_frame_url,
                "lastFrameUrl": last_frame_url,
            },
            output_summary={
                "fileUrl": video.output_url,
                "previewUrl": video.preview_url,
                "posterUrl": first_frame_url,
                "taskId": video.remote_task_id,
                "taskStatus": video.metadata.get("taskStatus", video.status),
                "durationSeconds": duration_seconds,
                "width": width,
                "height": height,
                "prompt": prompt,
                "runId": video.run_id,
            },
            model_call_summary={"runId": video.run_id, "modelInfo": video.model_info},
        )
        self._db.add(stage_version)
        if video.output_url:
            await self._mark_selected_version(workflow_id, clip_index, version_id)
            workflow.current_stage = WorkflowStage.JOINED.value
        else:
            workflow.current_stage = STAGE_VIDEO
        workflow.status = WorkflowStatus.READY.value
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    def _persist_video_asset(
        self,
        workflow: BizStageWorkflow,
        clip: dict[str, Any],
        clip_index: int,
        version_no: int,
        video: ParsedVideoResult,
        prompt: str,
        first_frame_url: str,
        last_frame_url: str,
    ) -> str:
        if not video.output_url:
            return ""
        asset = self._row_factory.create_material_asset(
            wf=workflow,
            stage_type=STAGE_VIDEO,
            clip_index=clip_index,
            version_no=version_no,
            media_type="video",
            title=f"镜头 {clip_index} 视频",
            public_url=video.output_url,
            mime_type=video.mime_type,
            width=video.width,
            height=video.height,
            duration_seconds=video.duration_seconds,
            origin_provider=trim(video.metadata.get("provider")),
            origin_model=trim(video.metadata.get("providerModel")),
            remote_task_id=video.remote_task_id,
            thumbnail_url=self._thumbnail_resolver(
                "video",
                video.output_url,
                [video.preview_url, first_frame_url, last_frame_url],
            ),
            metadata={"runId": video.run_id, "prompt": prompt, "clip": clip},
        )
        self._db.add(asset)
        return asset.material_asset_id

    async def _require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None,
    ) -> BizStageWorkflow | None:
        filters = [BizStageWorkflow.workflow_id == workflow_id, BizStageWorkflow.is_deleted == 0]
        if owner_user_id is not None:
            filters.append(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizStageWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def _require_storyboard_clip(
        self,
        workflow: BizStageWorkflow,
        clip_index: int,
    ) -> dict[str, Any]:
        versions = await self._list_stage_versions(workflow.workflow_id)
        storyboards = [version for version in versions if version.stage_type == STAGE_STORYBOARD]
        selected_id = trim(workflow.selected_storyboard_version_id)
        storyboard = next(
            (version for version in storyboards if selected_id and version.stage_version_id == selected_id),
            None,
        )
        if storyboard is None:
            storyboard = next((version for version in storyboards if version.selected == 1), None)
        if storyboard is None and storyboards:
            storyboard = storyboards[0]
        if storyboard is None:
            raise ValueError("请先选中一个分镜版本。")
        output = read_json_object(storyboard.output_summary_json)
        script = trim(output.get("scriptMarkdown") or output.get("previewText"))
        _, clips = parse_workflow_storyboard_markdown(script).to_view()
        clip = next((item for item in clips if safe_int(item.get("clipIndex"), 0) == clip_index), None)
        if clip is None:
            raise ValueError("镜头不存在，请重新选择分镜版本。")
        return clip

    async def _list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        result = await self._db.execute(
            select(BizStageVersion)
            .where(BizStageVersion.workflow_id == workflow_id, BizStageVersion.is_deleted == 0)
            .order_by(BizStageVersion.stage_type, BizStageVersion.clip_index, BizStageVersion.version_no.desc())
        )
        return list(result.scalars().all())

    async def _next_version_no(self, workflow_id: str, clip_index: int) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_VIDEO,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        return safe_int(result.scalar(), 0) + 1

    async def _mark_selected_version(
        self,
        workflow_id: str,
        clip_index: int,
        selected_version_id: str,
    ) -> None:
        result = await self._db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_VIDEO,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        timestamp = now_iso()
        for version in result.scalars().all():
            version.selected = 1 if version.stage_version_id == selected_version_id else 0
            version.update_time = timestamp
