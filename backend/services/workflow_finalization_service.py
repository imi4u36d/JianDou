"""Final video assembly for staged workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
from backend.domain.json_payloads import read_json_object
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import now_iso, safe_float, trim

logger = logging.getLogger(__name__)


class WorkflowFinalizationService:
    """Materialize selected clips and persist the final workflow asset."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        media_service: Any | None,
        row_factory: WorkflowPersistenceRowFactory,
        thumbnail_resolver: Callable[[str, str], str],
    ) -> None:
        self._db = db
        self._media_service = media_service
        self._row_factory = row_factory
        self._thumbnail_resolver = thumbnail_resolver

    async def finalize(
        self,
        workflow: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> BizMaterialAsset:
        selected_videos = self._selected_videos(versions)
        if not selected_videos:
            raise ValueError("请先为每个镜头选中视频版本。")

        total_duration = sum(
            safe_float(read_json_object(version.output_summary_json).get("durationSeconds"), 0.0)
            for version in selected_videos
        )
        joined_url = self._concat_selected_videos(workflow.workflow_id, selected_videos)
        public_url, metadata_note = self._final_output(joined_url, selected_videos)
        asset = self._row_factory.create_material_asset(
            wf=workflow,
            stage_type=WorkflowStage.JOINED.value,
            clip_index=0,
            version_no=1,
            media_type="video",
            title=f"{workflow.title} 完整视频",
            public_url=public_url,
            mime_type="video/mp4",
            width=0,
            height=0,
            duration_seconds=total_duration,
            thumbnail_url=self._thumbnail_resolver("video", public_url),
            metadata={
                "sourceVideoVersionIds": [version.stage_version_id for version in selected_videos],
                "note": metadata_note,
            },
        )
        self._db.add(asset)
        workflow.final_join_asset_id = asset.material_asset_id
        workflow.current_stage = WorkflowStage.JOINED.value
        workflow.status = WorkflowStatus.COMPLETED.value
        workflow.update_time = now_iso()
        await self._db.commit()
        return asset

    @staticmethod
    def _selected_videos(versions: list[BizStageVersion]) -> list[BizStageVersion]:
        selected = [
            version
            for version in versions
            if version.stage_type == WorkflowStage.VIDEO.value
            and version.selected == 1
            and trim(version.preview_url)
        ]
        return sorted(selected, key=lambda version: version.clip_index)

    def _concat_selected_videos(
        self,
        workflow_id: str,
        selected_videos: list[BizStageVersion],
    ) -> str:
        if self._media_service is None or len(selected_videos) <= 1:
            return ""
        try:
            local_urls = self._materialize_clips(workflow_id, selected_videos)
            if len(local_urls) < 2:
                return ""
            joined = self._media_service.concat_videos(
                f"tasks/{workflow_id}/joined",
                f"joined_{workflow_id}.mp4",
                local_urls,
            )
            joined_url = trim(getattr(joined, "public_url", ""))
            if joined_url:
                logger.info("Workflow %s: videos concatenated successfully → %s", workflow_id, joined_url)
            return joined_url
        except Exception as exc:
            logger.warning(
                "Workflow %s: video concatenation failed, falling back to preview: %s",
                workflow_id,
                exc,
            )
            return ""

    def _materialize_clips(
        self,
        workflow_id: str,
        selected_videos: list[BizStageVersion],
    ) -> list[str]:
        local_urls: list[str] = []
        for version in selected_videos:
            source_url = trim(version.download_url) or trim(version.preview_url)
            if not source_url:
                continue
            stored = self._media_service.materialize_artifact(
                source_url,
                f"tasks/{workflow_id}/clips",
                f"clip_{version.clip_index}.mp4",
            )
            local_urls.append(trim(getattr(stored, "public_url", "")) or source_url)
        return local_urls

    @staticmethod
    def _final_output(
        joined_url: str,
        selected_videos: list[BizStageVersion],
    ) -> tuple[str, str]:
        if joined_url:
            return joined_url, "已完成视频拼接。"
        first = selected_videos[0]
        public_url = trim(first.download_url) or trim(first.preview_url)
        if len(selected_videos) <= 1:
            return public_url, "当前环境使用首个已选视频作为成片预览"
        return public_url, "拼接失败，使用首个已选视频作为成片预览。请检查 ffmpeg 是否可用。"
