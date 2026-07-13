"""Task render-stage orchestration service."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_character_sheet_render_service import TaskCharacterSheetRenderService
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_frame_render_service import (
    GenerationApplicationServiceProtocol,
    TaskFrameRenderService,
)
from backend.services.task_render_reference_selector import (
    character_name_position,
    existing_character_sheet_urls,
    frame_reference_image_urls,
    matching_character_indexes,
)
from backend.services.task_render_stage_context import TaskRenderStageContext
from backend.services.task_render_stage_payloads import (
    FrameResolution,
    RenderStageRequest,
    RenderStageResult,
    build_frame_continuity_prompt,
    build_planning_stage_request,
    build_planning_stage_response,
)
from backend.services.task_worker_status_stage_service import TaskStage as _TaskStage
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService
from backend.shared import first_non_blank


class TaskWorkerRenderStageService:
    """Handles render planning: character sheets plus per-clip first/last keyframes."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceProtocol | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        if generation_application_service is None:
            raise RuntimeError("generation application service not configured")
        self._generation_application_service = generation_application_service
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler()
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
        )
        self._frame_render_service = TaskFrameRenderService(
            generation_application_service,
            self._runtime_support,
            self._artifact_assembler,
            self._status_stage_service,
            self._execution_coordinator,
            self._save_result,
        )
        self._character_sheet_service = TaskCharacterSheetRenderService(self)
        self._render_context = TaskRenderStageContext()

    async def _save_result(self, result: dict[str, Any] | None) -> None:
        """Persist coordinator mutations when the service is wired with a repository."""
        if self._task_repository is None or not result:
            return
        mutation = result.get("mutation")
        if isinstance(mutation, TaskPersistenceMutation):
            await self._task_repository.save_mutation(mutation)

    async def render(
        self, task: TaskRecord, run_context: TaskWorkerExecutionContext, request: RenderStageRequest
    ) -> RenderStageResult:
        image_run_ids: list[str] = []
        previous_clip_last_frame_url = request.previous_clip_last_frame_url
        character_sheet_urls = await self._ensure_character_sheets(
            task,
            run_context,
            request.character_definitions,
            request.width,
            request.height,
            image_run_ids,
        )

        if request.reuse_storyboard and request.render_start_index > 1:
            await self._save_result(
                self._execution_coordinator.record_trace(
                    task,
                    _TaskStage.PLANNING,
                    "planning.keyframe_reused_for_resume",
                    "检测到已有进度，跳过已完成镜头并从失败镜头继续。",
                    "INFO",
                    {
                        "completedClipCount": request.completed_clip_count,
                        "renderStartIndex": request.render_start_index,
                        "existingClipIndices": request.existing_video_clip_indices,
                        "lastFrameUrl": previous_clip_last_frame_url,
                        "resumeFromStage": request.requested_resume_stage,
                        "resumeFromClipIndex": request.requested_resume_clip_index,
                    },
                )
            )

        for index in range(max(0, request.render_start_index - 1), len(request.shot_plans)):
            self._runtime_support.assert_task_still_active(task)
            clip_index = index + 1
            shot_plan = request.shot_plans[index]

            clip_prompt = shot_plan.video_prompt()
            first_frame_prompt = first_non_blank(
                getattr(shot_plan, "first_frame_prompt", lambda: "")(),
                getattr(shot_plan, "last_frame_prompt", lambda: "")(),
                clip_prompt,
            )
            last_frame_prompt = first_non_blank(
                getattr(shot_plan, "last_frame_prompt", lambda: "")(),
                getattr(shot_plan, "first_frame_prompt", lambda: "")(),
                clip_prompt,
            )

            clip_duration = request.clip_duration_plan[index] if index < len(request.clip_duration_plan) else [0, 0, 0]
            clip_duration_seconds = clip_duration[0]

            reuse_previous_last_frame = clip_index > 1
            if reuse_previous_last_frame:
                if not previous_clip_last_frame_url.strip():
                    raise ValueError(
                        f"clip {clip_index} requires previous clip last frame before generating its end frame"
                    )
                start_frame = await self._reuse_frame(
                    task, clip_index, previous_clip_last_frame_url, "first", "previous_video_last_frame"
                )
                await self._save_result(
                    self._execution_coordinator.record_trace(
                        task,
                        _TaskStage.PLANNING,
                        "planning.keyframe_reused_from_last_frame",
                        "复用上一镜尾帧作为当前镜头首帧。",
                        "INFO",
                        {
                            "clipIndex": clip_index,
                            "firstFrameUrl": start_frame.video_input_url(),
                            "sourceLastFrameUrl": previous_clip_last_frame_url,
                        },
                    )
                )
            else:
                first_frame_references = self._frame_reference_image_urls(
                    first_frame_prompt,
                    previous_clip_last_frame_url,
                    character_sheet_urls,
                    request.character_definitions,
                )
                start_frame = await self._generate_frame(
                    task,
                    clip_index,
                    first_frame_prompt,
                    request.width,
                    request.height,
                    previous_clip_last_frame_url,
                    clip_duration_seconds,
                    "first",
                    "generated_start_frame_keyframe" if clip_index == 1 else "generated_start_frame_keyframe_fallback",
                    image_run_ids,
                    first_frame_references,
                )

            continuity_prompt = build_frame_continuity_prompt(
                shot_plan,
                last_frame_prompt,
                start_frame.prompt(),
                start_frame.video_input_url(),
                "last",
            )
            last_frame_references = self._frame_reference_image_urls(
                continuity_prompt,
                start_frame.video_input_url(),
                character_sheet_urls,
                request.character_definitions,
            )
            end_frame = await self._generate_frame(
                task,
                clip_index,
                continuity_prompt,
                request.width,
                request.height,
                start_frame.video_input_url(),
                clip_duration_seconds,
                "last",
                "generated_end_frame_keyframe",
                image_run_ids,
                last_frame_references,
            )

            self._render_context.record_clip(task, shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame)
            await self._task_repository.save(task) if self._task_repository else None

            await self._save_result(
                self._execution_coordinator.record_trace(
                    task,
                    _TaskStage.PLANNING,
                    "planning.clip_frames_resolved",
                    "当前分镜首尾帧约束已就绪。",
                    "INFO",
                    {
                        "clipIndex": clip_index,
                        "clipCount": len(request.shot_plans),
                        "startFrameUrl": start_frame.video_input_url(),
                        "startFrameSourceType": start_frame.source_type(),
                        "startFrameSourceUrl": start_frame.source_url(),
                        "endFrameConstraintUrl": end_frame.video_input_url(),
                        "endFrameConstraintSourceType": end_frame.source_type(),
                        "endFrameConstraintSourceUrl": end_frame.source_url(),
                    },
                )
            )
            await self._save_result(
                self._status_stage_service.record_stage_run(
                    task,
                    run_context,
                    100 + clip_index,
                    _TaskStage.PLANNING,
                    clip_index,
                    build_planning_stage_request(
                        task, clip_prompt, first_frame_prompt, last_frame_prompt, clip_duration_seconds
                    ),
                    build_planning_stage_response(start_frame, end_frame, reuse_previous_last_frame),
                )
            )

            previous_clip_last_frame_url = end_frame.material_url()
            self._render_context.record_clip_progress(task, clip_index, len(request.shot_plans), end_frame)
            await self._task_repository.save(task) if self._task_repository else None

        self._runtime_support.assert_task_still_active(task)
        self._render_context.complete(task, image_run_ids, len(request.shot_plans))
        await self._task_repository.save(task) if self._task_repository else None
        return RenderStageResult(image_run_ids, [], "", len(request.shot_plans))

    async def _generate_frame(
        self,
        task: TaskRecord,
        clip_index: int,
        prompt: str,
        width: int,
        height: int,
        reference_image_url: str,
        duration_seconds: int,
        frame_role: str,
        source_type: str,
        image_run_ids: list[str],
        reference_image_urls: list[str] | None = None,
    ) -> FrameResolution:
        return await self._frame_render_service.generate_frame(
            task,
            clip_index,
            prompt,
            width,
            height,
            reference_image_url,
            duration_seconds,
            frame_role,
            source_type,
            image_run_ids,
            reference_image_urls,
        )

    async def _ensure_character_sheets(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        character_definitions: list[Any],
        width: int,
        height: int,
        image_run_ids: list[str],
    ) -> list[str]:
        return await self._character_sheet_service.ensure_character_sheets(
            task,
            run_context,
            character_definitions,
            width,
            height,
            image_run_ids,
        )

    def _frame_reference_image_urls(
        self,
        prompt: str,
        scene_reference_url: str,
        character_sheet_urls: list[str],
        character_definitions: list[Any],
    ) -> list[str]:
        return frame_reference_image_urls(prompt, scene_reference_url, character_sheet_urls, character_definitions)

    def _matching_character_indexes(self, prompt: str, character_definitions: list[Any], sheet_count: int) -> list[int]:
        return matching_character_indexes(prompt, character_definitions, sheet_count)

    @staticmethod
    def _character_name_position(prompt: str, lowered_prompt: str, name: str) -> int:
        return character_name_position(prompt, lowered_prompt, name)

    def _existing_character_sheet_urls(self, task: TaskRecord) -> dict[int, str]:
        return existing_character_sheet_urls(task)

    async def _reuse_frame(
        self,
        task: TaskRecord,
        clip_index: int,
        source_url: str,
        frame_role: str,
        source_type: str,
    ) -> FrameResolution:
        return await self._frame_render_service.reuse_frame(
            task,
            clip_index,
            source_url,
            frame_role,
            source_type,
        )

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        self._render_context.put(task, key, value)
