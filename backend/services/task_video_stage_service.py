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
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator, TaskStateTransition
from backend.services.task_execution_runtime_support import GenerationModelKinds as _GenerationModelKinds
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_render_stage_payloads import RenderStageResult
from backend.services.task_video_clip_result_recorder import TaskVideoClipResultRecorder
from backend.services.task_video_join_service import TaskVideoJoinService
from backend.services.task_video_run_service import TaskVideoRunService
from backend.services.task_video_stage_context import TaskVideoStageContext
from backend.services.task_worker_status_stage_service import TaskStage as _TaskStage
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService
from backend.shared import safe_int, string_value


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
        self._video_run_service = TaskVideoRunService(generation_application_service)
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler(local_media_artifact_service)
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
        )
        self._local_media_artifact_service = local_media_artifact_service
        self._video_context = TaskVideoStageContext(self._runtime_support, local_media_artifact_service)
        self._clip_result_recorder = TaskVideoClipResultRecorder(
            self._video_context,
            self._artifact_assembler,
            self._status_stage_service,
            self._execution_coordinator,
            self._save_result,
            self._save_task,
        )
        self._video_join_service = TaskVideoJoinService(
            self._video_context,
            local_media_artifact_service,
            self._artifact_assembler,
            self._execution_coordinator,
            self._save_task,
            self._save_result,
        )

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
        await self._save_result(
            self._execution_coordinator.mark_active_attempt_running(task, resolved_context.worker_instance_id)
        )
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
        self._video_context.assert_can_continue(task)
        frame_contexts = self._video_context.clip_frame_contexts(task)
        if not frame_contexts:
            raise ValueError("任务缺少已解析的首尾帧上下文，无法继续生成视频。")

        clip_count = self._video_context.planned_clip_count(task, frame_contexts)
        existing_outputs = self._video_context.primary_video_outputs_by_clip(task)
        video_run_ids = self._video_context.context_video_run_ids(task)
        latest_video_output_url = self._video_context.latest_primary_video_url(task)

        for frame_context in frame_contexts:
            clip_index = safe_int(frame_context.get("clipIndex"), 0)
            if clip_index <= 0 or clip_index > clip_count:
                continue
            existing_output = existing_outputs.get(clip_index)
            if existing_output and self._video_context.output_url(existing_output):
                continue

            duration, min_duration, max_duration = self._video_context.duration_for_clip(
                task, frame_context, clip_index
            )
            first_frame_url = self._video_context.frame_input_url(frame_context, "start")
            last_frame_url = self._video_context.frame_input_url(frame_context, "end")
            if not first_frame_url:
                raise ValueError(f"clip {clip_index} 缺少首帧输入。")
            if not last_frame_url:
                raise ValueError(f"clip {clip_index} 缺少尾帧约束。")

            first_frame_remote_url = self._video_context.provider_frame_url(first_frame_url)
            last_frame_remote_url = self._video_context.provider_frame_url(last_frame_url)
            prompt = self._video_context.video_prompt_for_clip(task, frame_context, clip_index)
            video_size = self._video_context.video_size(task)

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
                submitted_run_id = self._video_context.submitted_video_run_id(task, frame_context, clip_index)
                if submitted_run_id:
                    video_run = await self._get_video_run(submitted_run_id)
                else:
                    video_run = await asyncio.wait_for(
                        self._generation_application_service.create_run(video_request),
                        timeout=max(30.0, float(opts.submit_timeout_seconds)),
                    )
                    submitted_run_id = string_value(video_run.get("id"))
                    if submitted_run_id:
                        self._video_context.mark_clip_video_submitted(task, clip_index, submitted_run_id)
                        if submitted_run_id not in video_run_ids:
                            video_run_ids.append(submitted_run_id)
                        self._video_context.put_execution_context(task, "clipVideoRunIds", video_run_ids)
                        self._video_context.put_execution_context(task, "videoRunId", submitted_run_id)
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

            recorded_clip = await self._clip_result_recorder.record(
                task,
                video_run,
                video_result,
                pending_model_call,
                clip_index,
                duration,
                min_duration,
                max_duration,
                first_frame_url,
                first_frame_remote_url,
                last_frame_url,
                video_run_ids,
            )
            latest_video_output_url = recorded_clip.output_url

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
        return await self._video_run_service.wait_for_run(video_run, options)

    async def _get_video_run(self, run_id: str) -> dict[str, Any]:
        return await self._video_run_service.get_run(run_id)

    def _successful_video_result(self, video_run: dict[str, Any]) -> dict[str, Any]:
        return self._video_run_service.successful_result(video_run)

    async def _join_if_ready(self, task: TaskRecord, clip_count: int) -> str:
        return await self._video_join_service.join_if_ready(task, clip_count)

    def _ensure_continue_attempt(self, task: TaskRecord) -> None:
        active_attempt = self._video_context.active_attempt(task)
        if active_attempt and string_value(active_attempt.get("status")) == AttemptStatus.RUNNING.value:
            return
        self._execution_coordinator.create_attempt(
            task,
            AttemptTriggerType.CONTINUE,
            {
                "resumeFromStage": _TaskStage.RENDER,
                "resumeFromClipIndex": self._video_context.next_missing_clip_index(task),
            },
        )

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
