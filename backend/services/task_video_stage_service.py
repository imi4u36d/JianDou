"""Task video-stage orchestration service.

This service owns the reusable task capability for turning resolved
first/last-frame constraints into clip videos, then joining contiguous clips.
Workflow orchestration can call this service instead of owning video generation
as workflow-only behavior.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from backend.domain.enums import AttemptStatus, AttemptTriggerType
from backend.domain.generation_run import GenerationRunStatuses
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import is_join, is_primary_video
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator, TaskStateTransition
from backend.services.task_execution_runtime_support import GenerationModelKinds as _GenerationModelKinds
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_render_stage_payloads import (
    RenderStageResult,
    resolved_last_frame_source_type,
    resolved_last_frame_source_url,
)
from backend.services.task_worker_status_stage_service import TaskStage as _TaskStage
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService
from backend.shared import first_non_blank, map_value, safe_int, string_value


class GenerationApplicationServiceProtocol(Protocol):
    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]: ...

    async def get_run(self, run_id: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class TaskVideoStageOptions:
    poll_interval_seconds: float = 10.0
    max_polls: int = 180
    join_videos: bool = True
    submit_timeout_seconds: float = 180.0


@dataclass(frozen=True)
class TaskVideoStageContinueResult:
    task_id: str
    video_run_ids: list[str]
    latest_video_output_url: str
    joined_output_url: str
    clip_count: int


class TaskVideoStageService:
    """Generate task clip videos from existing keyframes and join them."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceProtocol | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
        local_media_artifact_service: Any | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        if generation_application_service is None:
            raise RuntimeError("generation application service not configured")
        self._generation_application_service = generation_application_service
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler(local_media_artifact_service)
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
        )
        self._local_media_artifact_service = local_media_artifact_service

    async def continue_task(
        self,
        task_id: str,
        run_context: TaskWorkerExecutionContext | None = None,
        options: TaskVideoStageOptions | None = None,
    ) -> TaskVideoStageContinueResult:
        """Load a task and continue it from existing keyframes through join."""
        if self._task_repository is None:
            raise RuntimeError("task repository is required to continue a task")
        task = await self._task_repository.find_by_id(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        resolved_context = run_context or TaskWorkerExecutionContext(
            "task_video_continue",
            "task_video_stage",
            "manual",
        )
        self._ensure_continue_attempt(task)
        await self._save_result(self._execution_coordinator.mark_active_attempt_running(task, resolved_context.worker_instance_id))
        await self._transition(
            task,
            "RENDERING",
            max(70, min(95, task.progress or 70)),
            _TaskStage.RENDER,
            "task.video_continue_started",
            "任务继续生成视频片段。",
            {"workerInstanceId": resolved_context.worker_instance_id},
        )
        stage_result = await self.render_missing_videos(task, resolved_context, options)
        joined_output_url = string_value((task.execution_context or {}).get("latestJoinOutputUrl"))
        await self._save_result(
            self._execution_coordinator.transition_task(
                task,
                TaskStateTransition.info(
                    "COMPLETED",
                    100,
                    _TaskStage.PIPELINE,
                    "task.completed",
                    "任务视频生成与拼接已完成。",
                    {
                        "videoRunIds": stage_result.video_run_ids,
                        "clipCount": stage_result.clip_count,
                        "outputUrl": joined_output_url or stage_result.latest_video_output_url,
                    },
                ).with_attempt(AttemptStatus.FINISHED.value, ""),
            )
        )
        return TaskVideoStageContinueResult(
            task_id=task.id,
            video_run_ids=stage_result.video_run_ids,
            latest_video_output_url=stage_result.latest_video_output_url,
            joined_output_url=joined_output_url,
            clip_count=stage_result.clip_count,
        )

    async def render_missing_videos(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        options: TaskVideoStageOptions | None = None,
    ) -> RenderStageResult:
        """Generate missing clip videos for a task with resolved frame contexts."""
        opts = options or TaskVideoStageOptions()
        self._assert_task_can_continue(task)
        frame_contexts = self._clip_frame_contexts(task)
        if not frame_contexts:
            raise ValueError("任务缺少已解析的首尾帧上下文，无法继续生成视频。")

        clip_count = self._planned_clip_count(task, frame_contexts)
        existing_outputs = self._primary_video_outputs_by_clip(task)
        video_run_ids = self._context_video_run_ids(task)
        latest_video_output_url = self._latest_primary_video_url(task)

        for frame_context in frame_contexts:
            clip_index = safe_int(frame_context.get("clipIndex"), 0)
            if clip_index <= 0 or clip_index > clip_count:
                continue
            existing_output = existing_outputs.get(clip_index)
            if existing_output and self._output_url(existing_output):
                continue

            duration, min_duration, max_duration = self._duration_for_clip(task, frame_context, clip_index)
            first_frame_url = self._frame_input_url(frame_context, "start")
            last_frame_url = self._frame_input_url(frame_context, "end")
            if not first_frame_url:
                raise ValueError(f"clip {clip_index} 缺少首帧输入。")
            if not last_frame_url:
                raise ValueError(f"clip {clip_index} 缺少尾帧约束。")

            first_frame_remote_url = self._provider_frame_url(first_frame_url)
            last_frame_remote_url = self._provider_frame_url(last_frame_url)
            prompt = self._video_prompt_for_clip(task, frame_context, clip_index)
            video_size = self._video_size(task)

            await self._transition(
                task,
                "RENDERING",
                min(96, 70 + int(20 * (clip_index - 1) / max(1, clip_count))),
                _TaskStage.RENDER,
                "task.video_rendering",
                f"任务正在生成第 {clip_index}/{clip_count} 个视频片段。",
                {"clipIndex": clip_index, "clipCount": clip_count},
            )

            video_request = self._runtime_support.build_video_run_request(
                task,
                clip_index,
                prompt,
                video_size,
                duration,
                min_duration,
                max_duration,
                first_frame_remote_url,
                last_frame_remote_url,
            )
            pending_model_call = self._status_stage_service.create_pending_model_call(
                task,
                _TaskStage.RENDER,
                "generation.video",
                video_request,
                clip_index,
                _GenerationModelKinds.VIDEO,
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
            try:
                submitted_run_id = self._submitted_video_run_id(task, frame_context, clip_index)
                if submitted_run_id:
                    video_run = await self._get_video_run(submitted_run_id)
                else:
                    video_run = await asyncio.wait_for(
                        self._generation_application_service.create_run(video_request),
                        timeout=max(30.0, float(opts.submit_timeout_seconds)),
                    )
                    submitted_run_id = string_value(video_run.get("id"))
                    if submitted_run_id:
                        self._mark_clip_video_submitted(task, clip_index, submitted_run_id)
                        if submitted_run_id not in video_run_ids:
                            video_run_ids.append(submitted_run_id)
                        self._put_execution_context(task, "clipVideoRunIds", video_run_ids)
                        self._put_execution_context(task, "videoRunId", submitted_run_id)
                        await self._save_task(task)
                video_run = await self._wait_for_video_run(video_run, opts)
                video_result = self._successful_video_result(video_run)
            except Exception as ex:
                await self._save_result(
                    self._execution_coordinator.record_model_call(
                        task,
                        self._status_stage_service.fail_model_call(pending_model_call, ex),
                    )
                )
                raise

            video_model_call = self._status_stage_service.complete_model_call(
                pending_model_call,
                video_run,
                video_result,
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, video_model_call))
            self._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, video_run, video_result)
            video_material = self._artifact_assembler.create_video_material(
                task,
                video_run,
                video_result,
                clip_index,
                duration,
            )
            await self._save_result(self._execution_coordinator.record_material(task, video_material))

            video_metadata = map_value(video_result.get("metadata"))
            requested_last_frame_url = string_value(video_metadata.get("requestedLastFrameUrl"))
            provider_last_frame_url = string_value(video_metadata.get("lastFrameUrl"))
            extracted_last_frame_url = self._artifact_assembler.extract_last_frame_url(video_result)
            returned_last_frame_url = resolved_last_frame_source_url(
                extracted_last_frame_url,
                provider_last_frame_url,
                requested_last_frame_url or last_frame_url,
            )
            returned_last_frame_source_type = resolved_last_frame_source_type(
                extracted_last_frame_url,
                provider_last_frame_url,
                requested_last_frame_url or last_frame_url,
            )
            image_material = self._image_material_for_clip(task, clip_index, first_frame_url, first_frame_remote_url)
            video_output = self._artifact_assembler.create_result(
                task,
                video_run,
                video_result,
                video_material,
                image_material,
                video_model_call,
                returned_last_frame_url,
                clip_index,
                duration,
                min_duration,
                max_duration,
            )
            await self._save_result(self._execution_coordinator.record_result(task, video_output))

            video_run_id = string_value(video_run.get("id"))
            if video_run_id and video_run_id not in video_run_ids:
                video_run_ids.append(video_run_id)
            latest_video_output_url = first_non_blank(string_value(video_material.get("fileUrl")), self._output_url(video_output))
            self._update_clip_video_context(
                task,
                clip_index,
                video_run_id,
                latest_video_output_url,
                returned_last_frame_url,
                returned_last_frame_source_type,
            )
            self._put_execution_context(task, "clipVideoRunIds", video_run_ids)
            self._put_execution_context(task, "videoRunId", video_run_id)
            self._put_execution_context(task, "videoOutputUrl", latest_video_output_url)
            self._put_execution_context(task, "videoThumbnailUrl", string_value(video_result.get("thumbnailUrl")))
            self._put_execution_context(task, "videoRemoteTaskId", string_value(video_metadata.get("taskId")))
            self._put_execution_context(task, "videoRemoteSourceUrl", string_value(video_metadata.get("remoteSourceUrl")))
            self._put_execution_context(task, "lastFrameUrl", returned_last_frame_url)
            task.completed_output_count = max(task.completed_output_count, clip_index)
            await self._save_task(task)

        joined_output_url = ""
        if opts.join_videos:
            joined_output_url = await self._join_if_ready(task, clip_count)

        await self._transition(
            task,
            "RENDERING",
            98,
            _TaskStage.RENDER,
            "task.video_stage_completed",
            "任务视频片段生成与拼接阶段已完成。",
            {
                "videoRunIds": video_run_ids,
                "clipCount": clip_count,
                "latestVideoOutputUrl": latest_video_output_url,
                "latestJoinOutputUrl": joined_output_url,
            },
        )
        return RenderStageResult([], video_run_ids, joined_output_url or latest_video_output_url, clip_count)

    async def _wait_for_video_run(self, video_run: dict[str, Any], options: TaskVideoStageOptions) -> dict[str, Any]:
        current = dict(video_run or {})
        run_id = string_value(current.get("id"))
        for attempt in range(max(0, options.max_polls) + 1):
            status = string_value(current.get("status")).lower()
            if not GenerationRunStatuses.is_active(status):
                return current
            if attempt >= max(0, options.max_polls):
                break
            if options.poll_interval_seconds > 0:
                await asyncio.sleep(options.poll_interval_seconds)
            getter = getattr(self._generation_application_service, "get_run", None)
            if not callable(getter):
                break
            refreshed = await getter(run_id)
            if refreshed:
                current = dict(refreshed)
        raise RuntimeError(f"video run {run_id} did not finish within polling limit")

    async def _get_video_run(self, run_id: str) -> dict[str, Any]:
        getter = getattr(self._generation_application_service, "get_run", None)
        if not callable(getter):
            raise RuntimeError("generation service does not support run lookup")
        run = await getter(run_id)
        if not run:
            raise RuntimeError(f"video run {run_id} was not found")
        return dict(run)

    def _successful_video_result(self, video_run: dict[str, Any]) -> dict[str, Any]:
        status = string_value(video_run.get("status")).lower()
        result = map_value(video_run.get("result"))
        metadata = map_value(result.get("metadata"))
        if not GenerationRunStatuses.is_successful(status):
            error = first_non_blank(
                string_value(result.get("error")),
                string_value(metadata.get("error")),
                string_value(video_run.get("error")),
                status,
            )
            raise RuntimeError(f"video run failed: {error}")
        output_url = first_non_blank(
            string_value(result.get("outputUrl")),
            string_value(metadata.get("outputUrl")),
            string_value(metadata.get("fileUrl")),
            string_value(metadata.get("remoteSourceUrl")),
        )
        if not output_url:
            raise RuntimeError("video run succeeded without output url")
        return result

    async def _join_if_ready(self, task: TaskRecord, clip_count: int) -> str:
        if clip_count <= 1 or self._local_media_artifact_service is None:
            return ""
        existing_join = self._existing_join_for_clip_count(task, clip_count)
        if existing_join:
            join_url = self._output_url(existing_join)
            self._put_join_context(task, clip_count, join_url)
            await self._save_task(task)
            return join_url

        outputs_by_clip = self._primary_video_outputs_by_clip(task)
        source_urls: list[str] = []
        total_duration = 0.0
        for clip_index in range(1, clip_count + 1):
            output = outputs_by_clip.get(clip_index)
            url = self._output_url(output)
            if not url:
                return ""
            source_urls.append(url)
            total_duration += self._float_value(output.get("durationSeconds"), 0.0)
        if len(source_urls) < 2:
            return ""

        join_name = f"join-{clip_count}"
        joined = self._local_media_artifact_service.concat_videos(
            f"tasks/{task.id}/joined",
            f"{join_name}.mp4",
            source_urls,
        )
        join_material = self._artifact_assembler.create_join_material(
            task,
            joined,
            clip_count,
            source_urls,
            total_duration,
        )
        await self._save_result(self._execution_coordinator.record_material(task, join_material))
        join_result = self._artifact_assembler.create_join_result(
            task,
            join_material,
            clip_count,
            source_urls,
            total_duration,
        )
        await self._save_result(self._execution_coordinator.record_result(task, join_result))
        join_url = self._output_url(join_result)
        self._put_join_context(task, clip_count, join_url)
        await self._save_task(task)
        return join_url

    def _ensure_continue_attempt(self, task: TaskRecord) -> None:
        active_attempt = self._active_attempt(task)
        if active_attempt and string_value(active_attempt.get("status")) == AttemptStatus.RUNNING.value:
            return
        self._execution_coordinator.create_attempt(
            task,
            AttemptTriggerType.CONTINUE,
            {"resumeFromStage": _TaskStage.RENDER, "resumeFromClipIndex": self._next_missing_clip_index(task)},
        )

    def _assert_task_can_continue(self, task: TaskRecord) -> None:
        if string_value(task.task_type) and string_value(task.task_type) != "video_generation":
            raise ValueError("只有视频任务支持视频片段续跑。")
        if string_value(task.status).upper() in {"FAILED", "CANCELLED", "PAUSED"}:
            raise ValueError(f"任务当前状态为 {task.status}，不能继续生成视频。")

    def _clip_frame_contexts(self, task: TaskRecord) -> list[dict[str, Any]]:
        raw = (task.execution_context or {}).get("clipFrameContexts")
        rows = [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        rows.sort(key=lambda item: safe_int(item.get("clipIndex"), 0))
        return rows

    def _planned_clip_count(self, task: TaskRecord, frame_contexts: list[dict[str, Any]]) -> int:
        ctx = task.execution_context or {}
        return max(
            safe_int(ctx.get("plannedClipCount"), 0),
            safe_int(ctx.get("requestedOutputCount"), 0),
            len(frame_contexts),
        )

    def _next_missing_clip_index(self, task: TaskRecord) -> int:
        existing = set(self._primary_video_outputs_by_clip(task).keys())
        planned = self._planned_clip_count(task, self._clip_frame_contexts(task))
        for index in range(1, planned + 1):
            if index not in existing:
                return index
        return max(1, planned)

    def _primary_video_outputs_by_clip(self, task: TaskRecord) -> dict[int, dict[str, Any]]:
        rows: dict[int, dict[str, Any]] = {}
        for output in task.outputs or []:
            if not isinstance(output, dict) or not is_primary_video(output.get("resultType")):
                continue
            clip_index = safe_int(output.get("clipIndex"), 0)
            if clip_index > 0:
                rows[clip_index] = output
        return rows

    def _existing_join_for_clip_count(self, task: TaskRecord, clip_count: int) -> dict[str, Any]:
        expected = list(range(1, clip_count + 1))
        for output in task.outputs or []:
            if not isinstance(output, dict) or not is_join(output.get("resultType")):
                continue
            extra = map_value(output.get("extra"))
            if extra.get("clipIndices") == expected and self._output_url(output):
                return output
        return {}

    def _duration_for_clip(
        self,
        task: TaskRecord,
        frame_context: dict[str, Any],
        clip_index: int,
    ) -> tuple[int, int, int]:
        storyboard = self._storyboard_clip(task, clip_index)
        duration_row = self._duration_plan_row(task, clip_index)
        target = self._first_positive_int(
            frame_context.get("targetDurationSeconds"),
            storyboard.get("targetDurationSeconds"),
            duration_row.get("targetDurationSeconds"),
            task.min_duration_seconds,
            fallback=8,
        )
        min_duration = self._first_positive_int(
            storyboard.get("minDurationSeconds"),
            duration_row.get("minDurationSeconds"),
            target,
            fallback=target,
        )
        max_duration = self._first_positive_int(
            storyboard.get("maxDurationSeconds"),
            duration_row.get("maxDurationSeconds"),
            target,
            fallback=target,
        )
        target = max(1, target)
        min_duration = max(1, min_duration)
        max_duration = max(min_duration, max_duration)
        return target, min_duration, max_duration

    def _video_prompt_for_clip(self, task: TaskRecord, frame_context: dict[str, Any], clip_index: int) -> str:
        storyboard = self._storyboard_clip(task, clip_index)
        prompt = first_non_blank(
            storyboard.get("videoPrompt"),
            frame_context.get("videoPrompt"),
            frame_context.get("scene"),
            frame_context.get("startFramePrompt"),
            frame_context.get("endFramePrompt"),
        )
        if prompt:
            return prompt
        return first_non_blank(task.creative_prompt, task.title)

    def _video_size(self, task: TaskRecord) -> str:
        ctx = task.execution_context or {}
        configured = string_value(ctx.get("videoSize"))
        if configured:
            return configured
        width, height = self._runtime_support.resolve_dimensions(task)
        return f"{width}*{height}"

    def _storyboard_clip(self, task: TaskRecord, clip_index: int) -> dict[str, Any]:
        raw = (task.execution_context or {}).get("storyboardClips")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and safe_int(item.get("clipIndex"), 0) == clip_index:
                    return item
        return {}

    def _duration_plan_row(self, task: TaskRecord, clip_index: int) -> dict[str, Any]:
        raw = (task.execution_context or {}).get("clipDurationPlan")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and safe_int(item.get("clipIndex"), 0) == clip_index:
                    return item
        return {}

    def _frame_input_url(self, frame_context: dict[str, Any], role: str) -> str:
        if role == "start":
            return first_non_blank(
                frame_context.get("startFrameUrl"),
                frame_context.get("startFrameKeyframeUrl"),
                frame_context.get("startFrameSourceUrl"),
            )
        return first_non_blank(
            frame_context.get("endFrameConstraintUrl"),
            frame_context.get("endFrameKeyframeUrl"),
            frame_context.get("endFrameSourceUrl"),
        )

    def _provider_frame_url(self, frame_url: str) -> str:
        normalized = string_value(frame_url)
        if not normalized:
            return ""
        if normalized.lower().startswith(("http://", "https://", "data:")):
            return normalized
        publisher = getattr(self._local_media_artifact_service, "publish_local_artifact", None)
        if callable(publisher):
            return string_value(publisher(normalized))
        external = getattr(self._local_media_artifact_service, "build_externally_accessible_url", None)
        if callable(external):
            return string_value(external(normalized))
        return normalized

    def _image_material_for_clip(
        self,
        task: TaskRecord,
        clip_index: int,
        first_frame_url: str,
        first_frame_remote_url: str,
    ) -> dict[str, Any]:
        for material in task.materials or []:
            if not isinstance(material, dict):
                continue
            metadata = map_value(material.get("metadata"))
            if safe_int(material.get("clipIndex"), 0) != clip_index and safe_int(metadata.get("clipIndex"), 0) != clip_index:
                continue
            frame_role = first_non_blank(metadata.get("frameRole"), material.get("frameRole"))
            kind = first_non_blank(material.get("kind"), material.get("assetRole"))
            if frame_role == "first" or kind == "keyframe-first":
                return material
        return {"id": "", "fileUrl": first_frame_url, "previewUrl": first_frame_url, "remoteUrl": first_frame_remote_url}

    def _context_video_run_ids(self, task: TaskRecord) -> list[str]:
        raw = (task.execution_context or {}).get("clipVideoRunIds")
        if not isinstance(raw, list):
            return []
        return [string_value(item) for item in raw if string_value(item)]

    def _latest_primary_video_url(self, task: TaskRecord) -> str:
        latest_clip = 0
        latest_url = ""
        for clip_index, output in self._primary_video_outputs_by_clip(task).items():
            url = self._output_url(output)
            if url and clip_index >= latest_clip:
                latest_clip = clip_index
                latest_url = url
        return latest_url

    def _output_url(self, output: dict[str, Any] | None) -> str:
        if not output:
            return ""
        return first_non_blank(
            output.get("downloadUrl"),
            output.get("downloadPath"),
            output.get("previewUrl"),
            output.get("previewPath"),
        )

    def _update_clip_video_context(
        self,
        task: TaskRecord,
        clip_index: int,
        video_run_id: str,
        video_output_url: str,
        returned_last_frame_url: str,
        returned_last_frame_source_type: str,
    ) -> None:
        rows = self._clip_frame_contexts(task)
        for row in rows:
            if safe_int(row.get("clipIndex"), 0) != clip_index:
                continue
            row["videoRunId"] = video_run_id
            row["videoOutputUrl"] = video_output_url
            row["returnedLastFrameUrl"] = returned_last_frame_url
            row["returnedLastFrameSourceType"] = returned_last_frame_source_type
        self._put_execution_context(task, "clipFrameContexts", rows)

    def _submitted_video_run_id(self, task: TaskRecord, frame_context: dict[str, Any], clip_index: int) -> str:
        direct = string_value(frame_context.get("videoRunId"))
        if direct:
            return direct
        for row in self._clip_frame_contexts(task):
            if safe_int(row.get("clipIndex"), 0) == clip_index:
                return string_value(row.get("videoRunId"))
        return ""

    def _mark_clip_video_submitted(self, task: TaskRecord, clip_index: int, video_run_id: str) -> None:
        rows = self._clip_frame_contexts(task)
        for row in rows:
            if safe_int(row.get("clipIndex"), 0) == clip_index:
                row["videoRunId"] = video_run_id
        self._put_execution_context(task, "clipFrameContexts", rows)

    def _put_join_context(self, task: TaskRecord, clip_count: int, join_url: str) -> None:
        self._put_execution_context(task, "latestJoinName", f"join-{clip_count}")
        self._put_execution_context(task, "latestJoinOutputUrl", join_url)
        self._put_execution_context(task, "latestJoinClipIndices", list(range(1, clip_count + 1)))

    def _active_attempt(self, task: TaskRecord) -> dict[str, Any]:
        for attempt in task.attempts or []:
            if string_value(attempt.get("attemptId")) == string_value(task.active_attempt_id):
                return attempt
        return {}

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None:
            task.execution_context.pop(key, None)
            return
        if isinstance(value, str) and not value.strip():
            task.execution_context.pop(key, None)
            return
        task.execution_context[key] = value

    async def _transition(
        self,
        task: TaskRecord,
        next_status: str,
        progress: int,
        stage: str,
        event: str,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        await self._save_result(
            self._execution_coordinator.transition_task(
                task,
                TaskStateTransition.info(next_status, progress, stage, event, message, payload),
            )
        )

    async def _save_task(self, task: TaskRecord) -> None:
        if self._task_repository is not None:
            await self._task_repository.save(task)

    async def _save_result(self, result: dict[str, Any] | None) -> None:
        if self._task_repository is None or not result:
            return
        mutation = result.get("mutation")
        if isinstance(mutation, TaskPersistenceMutation):
            await self._task_repository.save_mutation(mutation)

    @staticmethod
    def _float_value(value: Any, fallback: float = 0.0) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip()) if value is not None else fallback
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _first_positive_int(*values: Any, fallback: int = 0) -> int:
        for value in values:
            resolved = safe_int(value, 0)
            if resolved > 0:
                return resolved
        return fallback
