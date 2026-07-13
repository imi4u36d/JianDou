"""Task worker and view services.

Translates the Java runtime pipeline services:
- TaskWorkerPipelineHandler
- TaskWorkerRenderStageService
- TaskWorkerStatusStageService
- TaskExecutionRuntimeSupport
- TaskExecutionArtifactAssembler
- JoinOutputService
- TaskViewMapper
"""

from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptStatus, TaskStatus, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.domain.task_resume import (
    existing_video_clip_indices,
    last_contiguous_completed_clip_index,
    resolve_resume_last_frame_url,
)
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.services.generation_service import (
    GenerationProviderException,
)
from backend.services.join_output_service import JoinOutputService
from backend.services.stubs import (
    GenerationApplicationServiceStub,
    LocalMediaArtifactServiceStub,
    TaskStoryboardPlannerStub,
)
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import (
    TaskExecutionCoordinator,
)
from backend.services.task_execution_runtime_support import (
    ModelRuntimePropertiesResolverStub,
    TaskExecutionRuntimeSupport,
)
from backend.services.task_render_stage_payloads import (
    RenderStageRequest,
)
from backend.services.task_storyboard_planner_adapter import TaskStoryboardPlannerAdapter
from backend.services.task_video_stage_service import TaskVideoStageService
from backend.services.task_worker_pipeline_composition import (
    build_task_worker_pipeline_collaborators,
)
from backend.services.task_worker_pipeline_context import (
    generation_result_map,
    is_video_generation_task,
    put_execution_context,
    stop_before_video_generation,
)
from backend.services.task_worker_render_stage_service import TaskWorkerRenderStageService
from backend.services.task_worker_status_stage_service import (
    TaskExecutionAbortedException,
    TaskWorkerExecutionContext,
    TaskWorkerStatusStageService,
)
from backend.services.task_worker_status_stage_service import (
    TaskStage as _TaskStage,
)
from backend.services.task_worker_view_mapper import TaskViewMapper
from backend.shared import now_iso, safe_int, string_value

# ---------------------------------------------------------------------------
# Module-level utility helpers (mirrors Java stringValue/intValue/firstNonBlank)
# ---------------------------------------------------------------------------


# ===================================================================
# TaskWorkerPipelineHandler
# ===================================================================


class TaskWorkerPipelineHandler:
    """Orchestrates the full task execution pipeline: analysis -> planning -> rendering -> join."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        task_queue_port: TaskQueuePort | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceStub | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        storyboard_planner: TaskStoryboardPlannerStub | TaskStoryboardPlannerAdapter | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
        render_stage_service: TaskWorkerRenderStageService | None = None,
        video_stage_service: TaskVideoStageService | None = None,
        join_stage_service: JoinOutputService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._task_queue_port = task_queue_port
        if generation_application_service is None:
            raise RuntimeError("generation application service not configured")
        self._generation_application_service = generation_application_service
        collaborators = build_task_worker_pipeline_collaborators(
            owner=self,
            task_repository=task_repository,
            generation_application_service=generation_application_service,
            execution_coordinator=execution_coordinator,
            runtime_support=runtime_support,
            artifact_assembler=artifact_assembler,
            storyboard_planner=storyboard_planner,
            status_stage_service=status_stage_service,
            render_stage_service=render_stage_service,
            video_stage_service=video_stage_service,
            join_stage_service=join_stage_service,
        )
        self._execution_coordinator = collaborators.execution_coordinator
        self._runtime_support = collaborators.runtime_support
        self._artifact_assembler = collaborators.artifact_assembler
        self._storyboard_planner = collaborators.storyboard_planner
        self._storyboard_preparation_service = collaborators.storyboard_preparation_service
        self._status_stage_service = collaborators.status_stage_service
        self._render_stage_service = collaborators.render_stage_service
        self._video_stage_service = collaborators.video_stage_service
        self._join_stage_service = collaborators.join_stage_service
        self._workspace_image_service = collaborators.workspace_image_service

    async def _save_result(self, result: dict[str, Any] | None) -> None:
        if self._task_repository is None or not result:
            return
        mutation = result.get("mutation")
        if isinstance(mutation, TaskPersistenceMutation):
            await self._task_repository.save_mutation(mutation)

    async def process_task(
        self,
        task_id: str,
        worker_instance_id: str,
        worker_type: str,
        execution_mode: str,
    ) -> None:
        run_context = TaskWorkerExecutionContext(worker_instance_id, worker_type, execution_mode)
        await self._process_task(task_id, run_context)

    async def _process_task(self, task_id: str, run_context: TaskWorkerExecutionContext) -> None:
        if self._task_repository is None:
            return
        task = await self._task_repository.find_by_id(task_id)
        if task is None:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task_id)
                if hasattr(result, "__await__"):
                    await result
            return
        if task.status != "PENDING" and TaskStatus(task.status) != TaskStatus.PENDING:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task_id)
                if hasattr(result, "__await__"):
                    await result
            return
        try:
            if self._task_queue_port:
                result = self._task_queue_port.remove(task.id)
                if hasattr(result, "__await__"):
                    await result
            task.is_queued = False
            task.queue_position = None
            if not task.started_at:
                task.started_at = now_iso()
            self._runtime_support.assert_task_still_active(task)
            active_attempt = self._runtime_support.active_attempt(task)

            if not is_video_generation_task(task):
                dimensions = self._runtime_support.resolve_workspace_image_dimensions(task)
                await self._process_workspace_image_task(task, run_context, dimensions)
                return

            dimensions = self._runtime_support.resolve_dimensions(task)
            duration_seconds = self._runtime_support.resolve_duration_seconds(task)
            video_size = f"{dimensions[0]}*{dimensions[1]}"
            existing_clip_indices = existing_video_clip_indices(task.outputs)
            completed_clip_count = last_contiguous_completed_clip_index(existing_clip_indices)
            render_start_index = max(1, completed_clip_count + 1)
            requested_resume_stage = string_value(active_attempt.get("resumeFromStage") if active_attempt else None)
            requested_resume_clip_index = safe_int(
                active_attempt.get("resumeFromClipIndex") if active_attempt else None,
                render_start_index,
            )
            reuse_storyboard = bool(requested_resume_stage) or completed_clip_count > 0

            self._put_execution_context(task, "durationSeconds", duration_seconds)
            self._put_execution_context(task, "videoSize", video_size)
            self._put_execution_context(task, "workerInstanceId", run_context.worker_instance_id)
            self._put_execution_context(task, "resumeExistingClipIndices", existing_clip_indices)
            self._put_execution_context(task, "resumeExistingOutputCount", completed_clip_count)
            self._put_execution_context(task, "resumeRenderFromClipIndex", render_start_index)
            self._put_execution_context(task, "attemptResumeFromStage", requested_resume_stage)
            self._put_execution_context(task, "attemptResumeFromClipIndex", requested_resume_clip_index)

            await self._save_result(
                self._execution_coordinator.mark_active_attempt_running(task, run_context.worker_instance_id)
            )
            await self._save_result(
                self._status_stage_service.update_status(
                    task,
                    run_context,
                    "ANALYZING",
                    5,
                    _TaskStage.ANALYSIS,
                    "task.claimed",
                    "任务已被执行节点领取。",
                )
            )
            self._runtime_support.assert_task_still_active(task)

            preparation = await self._storyboard_preparation_service.prepare(
                task,
                run_context,
                duration_seconds=duration_seconds,
                reuse_storyboard=reuse_storyboard,
                completed_clip_count=completed_clip_count,
                render_start_index=render_start_index,
                requested_resume_stage=requested_resume_stage,
                requested_resume_clip_index=requested_resume_clip_index,
            )
            script_run = preparation.script_run
            shot_plans = preparation.shot_plans
            character_definitions = preparation.character_definitions
            clip_duration_plan = preparation.clip_duration_plan
            render_request = RenderStageRequest(
                reuse_storyboard=reuse_storyboard,
                render_start_index=render_start_index,
                completed_clip_count=completed_clip_count,
                requested_resume_stage=requested_resume_stage,
                requested_resume_clip_index=requested_resume_clip_index,
                existing_video_clip_indices=existing_clip_indices,
                shot_plans=shot_plans,
                clip_duration_plan=clip_duration_plan,
                width=dimensions[0],
                height=dimensions[1],
                duration_seconds=duration_seconds,
                video_size=video_size,
                previous_clip_last_frame_url=resolve_resume_last_frame_url(
                    task.outputs, completed_clip_count, task.execution_context
                ),
                character_definitions=character_definitions,
            )
            render_result = await self._render_stage_service.render(task, run_context, render_request)
            final_render_result = render_result
            if not stop_before_video_generation(task):
                final_render_result = await self._video_stage_service.render_missing_videos(task, run_context)

            await self._save_result(
                self._status_stage_service.complete_task(
                    task,
                    run_context,
                    script_run,
                    render_result.image_run_ids,
                    final_render_result.video_run_ids,
                    final_render_result.clip_count,
                    final_render_result.latest_video_output_url,
                )
            )
            if self._join_stage_service and final_render_result.video_run_ids:
                self._join_stage_service.schedule_join(task.id, final_render_result.clip_count)

        except TaskExecutionAbortedException as ex:
            await self._save_result(self._status_stage_service.handle_abort(task, run_context, ex.task_status))
        except Exception as ex:
            await self._save_result(self._status_stage_service.fail_task(task, run_context, ex))

    async def _process_workspace_image_task(
        self, task: TaskRecord, run_context: TaskWorkerExecutionContext, dimensions: list[int]
    ) -> None:
        await self._workspace_image_service.process(task, run_context, dimensions)

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        put_execution_context(task, key, value)

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        return generation_result_map(run)


# ===================================================================
# Re-exports
# ===================================================================

__all__ = [
    "TaskWorkerPipelineHandler",
    "TaskWorkerRenderStageService",
    "TaskWorkerStatusStageService",
    "TaskExecutionRuntimeSupport",
    "TaskExecutionArtifactAssembler",
    "JoinOutputService",
    "TaskViewMapper",
    "TaskWorkerExecutionContext",
    "TaskExecutionAbortedException",
    "GenerationProviderException",
    "GenerationApplicationServiceStub",
    "LocalMediaArtifactServiceStub",
    "TaskStoryboardPlannerStub",
    "ModelRuntimePropertiesResolverStub",
]
