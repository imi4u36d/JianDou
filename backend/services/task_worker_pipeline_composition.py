"""Dependency composition for the task worker pipeline facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.infrastructure.task_repository import TaskRepository
from backend.services.join_output_service import JoinOutputService
from backend.services.stubs import GenerationApplicationServiceStub, TaskStoryboardPlannerStub
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_storyboard_planner_adapter import TaskStoryboardPlannerAdapter
from backend.services.task_storyboard_preparation_service import TaskStoryboardPreparationService
from backend.services.task_video_stage_service import TaskVideoStageService
from backend.services.task_worker_render_stage_service import TaskWorkerRenderStageService
from backend.services.task_worker_status_stage_service import TaskWorkerStatusStageService
from backend.services.task_workspace_image_service import TaskWorkspaceImageService


@dataclass(slots=True)
class TaskWorkerPipelineCollaborators:
    execution_coordinator: TaskExecutionCoordinator
    runtime_support: TaskExecutionRuntimeSupport
    artifact_assembler: TaskExecutionArtifactAssembler
    storyboard_planner: TaskStoryboardPlannerStub | TaskStoryboardPlannerAdapter
    storyboard_preparation_service: TaskStoryboardPreparationService
    status_stage_service: TaskWorkerStatusStageService
    render_stage_service: TaskWorkerRenderStageService
    video_stage_service: TaskVideoStageService
    join_stage_service: JoinOutputService | None
    workspace_image_service: TaskWorkspaceImageService


def build_task_worker_pipeline_collaborators(
    *,
    owner: Any,
    task_repository: TaskRepository | None,
    generation_application_service: GenerationApplicationServiceStub,
    execution_coordinator: TaskExecutionCoordinator | None = None,
    runtime_support: TaskExecutionRuntimeSupport | None = None,
    artifact_assembler: TaskExecutionArtifactAssembler | None = None,
    storyboard_planner: TaskStoryboardPlannerStub | TaskStoryboardPlannerAdapter | None = None,
    status_stage_service: TaskWorkerStatusStageService | None = None,
    render_stage_service: TaskWorkerRenderStageService | None = None,
    video_stage_service: TaskVideoStageService | None = None,
    join_stage_service: JoinOutputService | None = None,
) -> TaskWorkerPipelineCollaborators:
    coordinator = execution_coordinator or TaskExecutionCoordinator()
    runtime = runtime_support or TaskExecutionRuntimeSupport()
    artifacts = artifact_assembler or TaskExecutionArtifactAssembler()
    planner = storyboard_planner or TaskStoryboardPlannerAdapter()
    status = status_stage_service or TaskWorkerStatusStageService(
        task_repository=task_repository,
        execution_coordinator=coordinator,
    )
    render = render_stage_service or TaskWorkerRenderStageService(
        task_repository=task_repository,
        execution_coordinator=coordinator,
        generation_application_service=generation_application_service,
        runtime_support=runtime,
        artifact_assembler=artifacts,
        status_stage_service=status,
    )
    video = video_stage_service or TaskVideoStageService(
        task_repository=task_repository,
        execution_coordinator=coordinator,
        generation_application_service=generation_application_service,
        runtime_support=runtime,
        artifact_assembler=artifacts,
        status_stage_service=status,
        local_media_artifact_service=getattr(artifacts, "_local_media_artifact_service", None),
    )
    return TaskWorkerPipelineCollaborators(
        execution_coordinator=coordinator,
        runtime_support=runtime,
        artifact_assembler=artifacts,
        storyboard_planner=planner,
        storyboard_preparation_service=TaskStoryboardPreparationService(
            task_repository,
            generation_application_service,
            runtime,
            artifacts,
            planner,
            status,
            coordinator,
            owner._save_result,
        ),
        status_stage_service=status,
        render_stage_service=render,
        video_stage_service=video,
        join_stage_service=join_stage_service,
        workspace_image_service=TaskWorkspaceImageService(owner),
    )
