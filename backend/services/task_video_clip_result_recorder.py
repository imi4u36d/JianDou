"""Persist a successful generated video clip and update task context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from backend.domain.media_result import remote_source_url
from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_render_stage_payloads import (
    resolved_last_frame_source_type,
    resolved_last_frame_source_url,
)
from backend.services.task_video_stage_context import TaskVideoStageContext
from backend.services.task_worker_status_stage_service import TaskStage, TaskWorkerStatusStageService
from backend.shared import first_non_blank, map_value, string_value


@dataclass(frozen=True)
class RecordedVideoClip:
    run_id: str
    output_url: str


class TaskVideoClipResultRecorder:
    def __init__(
        self,
        context: TaskVideoStageContext,
        artifact_assembler: TaskExecutionArtifactAssembler,
        status_service: TaskWorkerStatusStageService,
        coordinator: TaskExecutionCoordinator,
        save_result: Callable[[dict[str, Any] | None], Awaitable[None]],
        save_task: Callable[[TaskRecord], Awaitable[None]],
    ) -> None:
        self._context = context
        self._artifacts = artifact_assembler
        self._status = status_service
        self._coordinator = coordinator
        self._save_result = save_result
        self._save_task = save_task

    async def record(
        self,
        task: TaskRecord,
        video_run: dict[str, Any],
        video_result: dict[str, Any],
        pending_model_call: dict[str, Any],
        clip_index: int,
        duration: int,
        min_duration: int,
        max_duration: int,
        first_frame_url: str,
        first_frame_remote_url: str,
        requested_last_frame_url: str,
        video_run_ids: list[str],
    ) -> RecordedVideoClip:
        model_call = self._status.complete_model_call(
            pending_model_call,
            video_run,
            video_result,
        )
        await self._save_result(self._coordinator.record_model_call(task, model_call))
        self._status.record_run_call_chain(task, TaskStage.RENDER, video_run, video_result)
        material = self._artifacts.create_video_material(
            task,
            video_run,
            video_result,
            clip_index,
            duration,
        )
        await self._save_result(self._coordinator.record_material(task, material))

        metadata = map_value(video_result.get("metadata"))
        provider_last_frame_url = string_value(metadata.get("lastFrameUrl"))
        provider_requested_url = string_value(metadata.get("requestedLastFrameUrl"))
        extracted_last_frame_url = self._artifacts.extract_last_frame_url(video_result)
        fallback_last_frame_url = provider_requested_url or requested_last_frame_url
        returned_last_frame_url = resolved_last_frame_source_url(
            extracted_last_frame_url,
            provider_last_frame_url,
            fallback_last_frame_url,
        )
        returned_last_frame_source_type = resolved_last_frame_source_type(
            extracted_last_frame_url,
            provider_last_frame_url,
            fallback_last_frame_url,
        )
        image_material = self._context.image_material_for_clip(
            task,
            clip_index,
            first_frame_url,
            first_frame_remote_url,
        )
        output = self._artifacts.create_result(
            task,
            video_run,
            video_result,
            material,
            image_material,
            model_call,
            returned_last_frame_url,
            clip_index,
            duration,
            min_duration,
            max_duration,
        )
        await self._save_result(self._coordinator.record_result(task, output))

        run_id = string_value(video_run.get("id"))
        if run_id and run_id not in video_run_ids:
            video_run_ids.append(run_id)
        output_url = first_non_blank(
            string_value(material.get("fileUrl")),
            self._context.output_url(output),
        )
        self._context.update_clip_video_context(
            task,
            clip_index,
            run_id,
            output_url,
            returned_last_frame_url,
            returned_last_frame_source_type,
        )
        context_values = {
            "clipVideoRunIds": video_run_ids,
            "videoRunId": run_id,
            "videoOutputUrl": output_url,
            "videoThumbnailUrl": string_value(video_result.get("thumbnailUrl")),
            "videoRemoteTaskId": string_value(metadata.get("taskId")),
            "videoRemoteSourceUrl": remote_source_url(metadata),
            "lastFrameUrl": returned_last_frame_url,
        }
        for key, value in context_values.items():
            self._context.put_execution_context(task, key, value)
        task.completed_output_count = max(task.completed_output_count, clip_index)
        await self._save_task(task)
        return RecordedVideoClip(run_id, output_url)
