"""Joined-output creation for completed task video clips."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_video_stage_context import TaskVideoStageContext


class TaskVideoJoinService:
    def __init__(
        self,
        context: TaskVideoStageContext,
        media_service: Any | None,
        artifact_assembler: TaskExecutionArtifactAssembler,
        execution_coordinator: TaskExecutionCoordinator,
        save_task: Callable[[TaskRecord], Awaitable[None]],
        save_result: Callable[[dict[str, Any] | None], Awaitable[None]],
    ) -> None:
        self._context = context
        self._media_service = media_service
        self._artifact_assembler = artifact_assembler
        self._execution_coordinator = execution_coordinator
        self._save_task = save_task
        self._save_result = save_result

    async def join_if_ready(self, task: TaskRecord, clip_count: int) -> str:
        if clip_count <= 1 or self._media_service is None:
            return ""
        existing_join = self._context.existing_join_for_clip_count(task, clip_count)
        if existing_join:
            join_url = self._context.output_url(existing_join)
            self._context.put_join_context(task, clip_count, join_url)
            await self._save_task(task)
            return join_url

        outputs_by_clip = self._context.primary_video_outputs_by_clip(task)
        source_urls: list[str] = []
        total_duration = 0.0
        for clip_index in range(1, clip_count + 1):
            output = outputs_by_clip.get(clip_index)
            url = self._context.output_url(output)
            if not url:
                return ""
            source_urls.append(url)
            total_duration += self._context.float_value(output.get("durationSeconds"), 0.0)
        if len(source_urls) < 2:
            return ""

        join_name = f"join-{clip_count}"
        joined = self._media_service.concat_videos(
            f"tasks/{task.id}/joined",
            f"{join_name}.mp4",
            source_urls,
        )
        join_material = self._artifact_assembler.create_join_material(
            task, joined, clip_count, source_urls, total_duration
        )
        await self._save_result(self._execution_coordinator.record_material(task, join_material))
        join_result = self._artifact_assembler.create_join_result(
            task, join_material, clip_count, source_urls, total_duration
        )
        await self._save_result(self._execution_coordinator.record_result(task, join_result))
        join_url = self._context.output_url(join_result)
        self._context.put_join_context(task, clip_count, join_url)
        await self._save_task(task)
        return join_url
