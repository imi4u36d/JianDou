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

import uuid
from collections.abc import Callable
from typing import Any, Optional

from backend.domain.enums import AttemptStatus, TaskStatus, WorkerStatus
from backend.domain.task_record import TaskRecord
from backend.domain.task_resume import (
    existing_video_clip_indices,
    last_contiguous_completed_clip_index,
    resolve_resume_last_frame_url,
)
from backend.domain.task_storyboard_planner import TaskStoryboardPlanner
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_queue_port import TaskQueuePort
from backend.infrastructure.task_repository import TaskRepository
from backend.services.generation_service import (
    GenerationProviderException,
)
from backend.services.stubs import (
    GenerationApplicationServiceStub,
    LocalMediaArtifactServiceStub,
    TaskStoryboardPlannerStub,
)
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler, _TaskArtifactNaming
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
from backend.shared import first_non_blank, map_value, now_iso, safe_int, string_value

# ---------------------------------------------------------------------------
# Module-level utility helpers (mirrors Java stringValue/intValue/firstNonBlank)
# ---------------------------------------------------------------------------


class _GenerationRunKinds:
    SCRIPT = "script"
    IMAGE = "image"
    VIDEO = "video"


class TaskStoryboardPlannerAdapter:
    """Adapts the real storyboard planner to the worker's shot-plan interface."""

    def __init__(self, planner: TaskStoryboardPlanner | None = None) -> None:
        self._planner = planner or TaskStoryboardPlanner()

    def build_storyboard_shot_plans(
        self, task: TaskRecord, storyboard_markdown: str
    ) -> list[TaskStoryboardPlannerStub.StoryboardShotPlan]:
        plans: list[TaskStoryboardPlannerStub.StoryboardShotPlan] = []
        for plan in self._planner.build_storyboard_shot_plans(task, storyboard_markdown):
            plans.append(
                TaskStoryboardPlannerStub.StoryboardShotPlan(
                    sequential_index=safe_int(getattr(plan, "sequential_index", 0), len(plans) + 1),
                    shot_label=string_value(getattr(plan, "shot_label", "")),
                    scene=string_value(getattr(plan, "scene", "")),
                    video_prompt=string_value(getattr(plan, "video_prompt", "")),
                    image_prompt=string_value(getattr(plan, "image_prompt", "")),
                    first_frame_prompt=string_value(getattr(plan, "first_frame_prompt", "")),
                    last_frame_prompt=string_value(getattr(plan, "last_frame_prompt", "")),
                    motion=string_value(getattr(plan, "motion", "")),
                    camera_movement=string_value(getattr(plan, "camera_movement", "")),
                    duration_hint=string_value(getattr(plan, "duration_hint", "")),
                )
            )
        return plans

    def extract_character_definitions(self, storyboard_markdown: str) -> list[Any]:
        return self._planner.extract_character_definitions(storyboard_markdown)

    def resolve_requested_output_count(self, task: TaskRecord, storyboard_clip_count: int) -> int:
        return self._planner.resolve_requested_output_count(task, storyboard_clip_count)

    def extract_storyboard_shot_duration_ranges(self, storyboard_markdown: str) -> list[list[int]]:
        return self._planner.extract_storyboard_shot_duration_ranges(storyboard_markdown)

    def build_clip_duration_plan(
        self, task: TaskRecord, duration_seconds: int, clip_count: int, storyboard_markdown: str
    ) -> list[list[int]]:
        return self._planner.build_clip_duration_plan(task, duration_seconds, clip_count, storyboard_markdown)

    def normalize_clip_duration_plan(self, video_model: str, clip_duration_plan: list[list[int]]) -> list[list[int]]:
        return self._planner.normalize_clip_duration_plan(video_model, clip_duration_plan)

    def request_snapshot_output_count(self, task: TaskRecord) -> Any:
        return self._planner.request_snapshot_output_count(task)

    def build_clip_duration_plan_context(
        self, clip_duration_plan: list[list[int]], duration_ranges: list[list[int]]
    ) -> list[dict[str, Any]]:
        return self._planner.build_clip_duration_plan_context(clip_duration_plan, duration_ranges)


# ===================================================================
# JoinOutputService
# ===================================================================


class JoinOutputService:
    """Service for concatenating video clip outputs into a single joined output."""

    JOIN_OUTPUT_CLIP_INDEX_BASE = 10000

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        local_media_artifact_service: LocalMediaArtifactServiceStub | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        self._local_media_artifact_service = local_media_artifact_service
        self._join_worker_instance_id = f"spring_join_worker_{uuid.uuid4().hex}"

    def schedule_join(self, task_id: str, end_clip_index: int) -> None:
        """Stub: schedule join would use a thread pool in production."""
        pass

    def _join_output_name(self, end_clip_index: int) -> str:
        if end_clip_index <= 1:
            return "join-1"
        return _TaskArtifactNaming.join_name(end_clip_index)


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
        join_stage_service: JoinOutputService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._task_queue_port = task_queue_port
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        if generation_application_service is None:
            raise RuntimeError("generation application service not configured")
        self._generation_application_service = generation_application_service
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler()
        self._storyboard_planner = storyboard_planner or TaskStoryboardPlannerAdapter()
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
        )
        self._render_stage_service = render_stage_service or TaskWorkerRenderStageService(
            task_repository=task_repository,
            execution_coordinator=self._execution_coordinator,
            generation_application_service=self._generation_application_service,
            runtime_support=self._runtime_support,
            artifact_assembler=self._artifact_assembler,
            status_stage_service=self._status_stage_service,
        )
        self._join_stage_service = join_stage_service

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
            dimensions = self._runtime_support.resolve_dimensions(task)

            if not self._is_video_generation_task(task):
                await self._process_workspace_image_task(task, run_context, dimensions)
                return

            duration_seconds = self._runtime_support.resolve_duration_seconds(task)
            video_size = f"{dimensions[0]}*{dimensions[1]}"
            existing_video_clip_indices = self._existing_video_clip_indices(task)
            completed_clip_count = self._last_contiguous_completed_clip_index(existing_video_clip_indices)
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
            self._put_execution_context(task, "resumeExistingClipIndices", existing_video_clip_indices)
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

            script_run: dict[str, Any] = {}
            storyboard_markdown = ""

            if reuse_storyboard and task.storyboard_script and task.storyboard_script.strip():
                storyboard_markdown = task.storyboard_script
                await self._save_result(
                    self._execution_coordinator.record_trace(
                        task,
                        _TaskStage.ANALYSIS,
                        "analysis.reused",
                        "检测到已有分镜脚本，跳过分析并继续后续镜头。",
                        "INFO",
                        {
                            "completedClipCount": completed_clip_count,
                            "renderStartIndex": render_start_index,
                            "resumeFromStage": requested_resume_stage,
                            "resumeFromClipIndex": requested_resume_clip_index,
                        },
                    )
                )
            else:
                await self._save_result(
                    self._status_stage_service.update_status(
                        task,
                        run_context,
                        "ANALYZING",
                        10,
                        _TaskStage.ANALYSIS,
                        "task.analyzing",
                        "任务开始分析文本与镜头约束。",
                    )
                )

                script_request = self._runtime_support.build_script_run_request(task)
                pending_model_call = self._status_stage_service.create_pending_model_call(
                    task,
                    _TaskStage.ANALYSIS,
                    "generation.script",
                    script_request,
                    1,
                    "script",
                )
                await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
                try:
                    script_run = await self._generation_application_service.create_run(script_request)
                except Exception as ex:
                    await self._save_result(
                        self._execution_coordinator.record_model_call(
                            task, self._status_stage_service.fail_model_call(pending_model_call, ex)
                        )
                    )
                    raise

                self._runtime_support.assert_task_still_active(task)
                script_result = self._result_map(script_run)
                storyboard_markdown = string_value(script_result.get("scriptMarkdown"))
                if not storyboard_markdown:
                    raise ValueError("分镜脚本为空，未生成有效输出。")
                task.storyboard_script = storyboard_markdown
                self._put_execution_context(task, "analysisRunId", string_value(script_run.get("id")))
                self._put_execution_context(task, "scriptRunId", string_value(script_run.get("id")))
                self._put_execution_context(task, "analysisScriptText", storyboard_markdown)
                self._put_execution_context(task, "analysisPrompt", string_value(script_result.get("prompt")))
                await self._task_repository.save(task)

                await self._save_result(
                    self._status_stage_service.record_stage_run(
                        task,
                        run_context,
                        1,
                        _TaskStage.ANALYSIS,
                        1,
                        {"title": task.title, "aspectRatio": task.aspect_ratio},
                        {"summary": "文本分析完成", "scriptRunId": string_value(script_run.get("id"))},
                    )
                )
                analysis_model_call = self._status_stage_service.complete_model_call(
                    pending_model_call, script_run, script_result
                )
                await self._save_result(self._execution_coordinator.record_model_call(task, analysis_model_call))
                self._status_stage_service.record_run_call_chain(task, _TaskStage.ANALYSIS, script_run, script_result)
                script_material = self._artifact_assembler.create_text_material(task, script_run, script_result)
                await self._save_result(self._execution_coordinator.record_material(task, script_material))
                self._put_execution_context(task, "storyboardFileUrl", string_value(script_material.get("fileUrl")))
                await self._task_repository.save(task)

            shot_plans = self._storyboard_planner.build_storyboard_shot_plans(task, storyboard_markdown)
            character_definitions = self._storyboard_planner.extract_character_definitions(storyboard_markdown)
            storyboard_clip_count = len(shot_plans)
            requested_output_count = self._storyboard_planner.resolve_requested_output_count(
                task, storyboard_clip_count
            )
            if requested_output_count < len(shot_plans):
                shot_plans = list(shot_plans[:requested_output_count])

            clip_prompts = [sp.video_prompt() for sp in shot_plans]
            storyboard_duration_ranges = self._storyboard_planner.extract_storyboard_shot_duration_ranges(
                storyboard_markdown
            )
            clip_duration_plan = self._storyboard_planner.build_clip_duration_plan(
                task, duration_seconds, len(clip_prompts), storyboard_markdown
            )
            snapshot = task.request_snapshot or {}
            clip_duration_plan = self._storyboard_planner.normalize_clip_duration_plan(
                string_value(snapshot.get("videoModel", "")),
                clip_duration_plan,
            )
            self._put_execution_context(task, "storyboardClipCount", storyboard_clip_count)
            self._put_execution_context(
                task, "requestedOutputCount", self._storyboard_planner.request_snapshot_output_count(task)
            )
            self._put_execution_context(task, "plannedClipCount", len(clip_prompts))
            self._put_execution_context(task, "characterDefinitionCount", len(character_definitions))
            self._put_execution_context(
                task, "characterDefinitions", self._build_character_definition_context(character_definitions)
            )
            self._put_execution_context(task, "clipPrompts", clip_prompts)
            self._put_execution_context(
                task,
                "clipDurationPlan",
                self._storyboard_planner.build_clip_duration_plan_context(
                    clip_duration_plan, storyboard_duration_ranges
                ),
            )
            self._put_execution_context(task, "storyboardFormatVersion", "structured-md-v1")
            self._put_execution_context(task, "storyboardContinuityRule", "current_end_frame_matches_next_start_frame")
            self._put_execution_context(
                task, "storyboardClips", self._build_storyboard_clip_context(shot_plans, clip_duration_plan)
            )
            await self._task_repository.save(task)

            await self._save_result(
                self._execution_coordinator.record_trace(
                    task,
                    _TaskStage.PLANNING,
                    "planning.shots_resolved",
                    "已完成分镜数量解析，按镜头顺序生成。",
                    "INFO",
                    {
                        "clipCount": len(clip_prompts),
                        "storyboardClipCount": storyboard_clip_count,
                        "requestedOutputCount": self._storyboard_planner.request_snapshot_output_count(task),
                        "completedClipCount": completed_clip_count,
                        "renderStartIndex": render_start_index,
                    },
                )
            )

            await self._save_result(
                self._status_stage_service.update_status(
                    task,
                    run_context,
                    "PLANNING",
                    35,
                    _TaskStage.PLANNING,
                    "task.planning",
                    "任务开始按分镜生成关键画面。",
                )
            )

            render_request = RenderStageRequest(
                reuse_storyboard=reuse_storyboard,
                render_start_index=render_start_index,
                completed_clip_count=completed_clip_count,
                requested_resume_stage=requested_resume_stage,
                requested_resume_clip_index=requested_resume_clip_index,
                existing_video_clip_indices=existing_video_clip_indices,
                shot_plans=shot_plans,
                clip_duration_plan=clip_duration_plan,
                width=dimensions[0],
                height=dimensions[1],
                duration_seconds=duration_seconds,
                video_size=video_size,
                previous_clip_last_frame_url=self._resolve_resume_last_frame_url(task, completed_clip_count),
                character_definitions=character_definitions,
            )
            render_result = await self._render_stage_service.render(task, run_context, render_request)

            await self._save_result(
                self._status_stage_service.complete_task(
                    task,
                    run_context,
                    script_run,
                    render_result.image_run_ids,
                    render_result.video_run_ids,
                    render_result.clip_count,
                    render_result.latest_video_output_url,
                )
            )
            if self._join_stage_service and render_result.video_run_ids:
                self._join_stage_service.schedule_join(task.id, render_result.clip_count)

        except TaskExecutionAbortedException as ex:
            await self._save_result(self._status_stage_service.handle_abort(task, run_context, ex.task_status))
        except Exception as ex:
            await self._save_result(self._status_stage_service.fail_task(task, run_context, ex))

    async def _process_workspace_image_task(
        self, task: TaskRecord, run_context: TaskWorkerExecutionContext, dimensions: list[int]
    ) -> None:
        output_count = self._runtime_support.resolve_workspace_image_output_count(task)
        self._put_execution_context(task, "imageSize", f"{dimensions[0]}x{dimensions[1]}")
        self._put_execution_context(task, "requestedImageOutputCount", output_count)
        self._put_execution_context(task, "workerInstanceId", run_context.worker_instance_id)
        await self._save_result(
            self._execution_coordinator.mark_active_attempt_running(task, run_context.worker_instance_id)
        )
        await self._save_result(
            self._status_stage_service.update_status(
                task,
                run_context,
                "RENDERING",
                5,
                _TaskStage.RENDER,
                "task.claimed",
                "任务已被 worker 领取。",
            )
        )
        self._runtime_support.assert_task_still_active(task)

        await self._save_result(
            self._status_stage_service.update_status(
                task,
                run_context,
                "RENDERING",
                40,
                _TaskStage.RENDER,
                "task.rendering",
                "工作台图片任务开始生成。",
            )
        )

        image_run_ids: list[str] = []
        output_urls: list[str] = []
        material_asset_ids: list[str] = []
        latest_image_run: dict[str, Any] = {}
        latest_output_url = ""

        for output_index in range(1, output_count + 1):
            if output_count > 1:
                progress = min(92, 40 + int((output_index - 1) * 45 / output_count))
                await self._save_result(
                    self._status_stage_service.update_status(
                        task,
                        run_context,
                        "RENDERING",
                        progress,
                        _TaskStage.RENDER,
                        "task.rendering",
                        f"工作台图片任务正在生成第 {output_index}/{output_count} 张。",
                    )
                )

            image_request = self._runtime_support.build_workspace_image_run_request(
                task,
                dimensions[0],
                dimensions[1],
                output_index=output_index,
            )
            pending_model_call = self._status_stage_service.create_pending_model_call(
                task,
                _TaskStage.RENDER,
                "generation.image",
                image_request,
                output_index,
                "workspace_image",
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
            try:
                image_run = await self._generation_application_service.create_run(image_request)
            except Exception as ex:
                await self._save_result(
                    self._execution_coordinator.record_model_call(
                        task, self._status_stage_service.fail_model_call(pending_model_call, ex)
                    )
                )
                raise
            self._runtime_support.assert_task_still_active(task)
            image_result = self._result_map(image_run)
            image_metadata = map_value(image_result.get("metadata"))
            output_url = first_non_blank(
                string_value(image_result.get("outputUrl")),
                string_value(image_metadata.get("outputUrl")),
                string_value(image_metadata.get("fileUrl")),
            )
            if not output_url:
                raise ValueError("图片生成结果为空，未返回可用输出地址。")

            image_model_call = self._status_stage_service.complete_model_call(
                pending_model_call, image_run, image_result
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, image_model_call))
            self._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, image_run, image_result)
            image_material = self._artifact_assembler.create_workspace_image_material(
                task,
                image_run,
                image_result,
                output_index=output_index,
            )
            await self._save_result(self._execution_coordinator.record_material(task, image_material))
            stored_output_url = first_non_blank(string_value(image_material.get("fileUrl")), output_url)
            image_output = self._artifact_assembler.create_image_result(
                task,
                image_run,
                image_result,
                image_material,
                image_model_call,
                output_index=output_index,
            )
            await self._save_result(self._execution_coordinator.record_result(task, image_output))
            image_run_id = string_value(image_run.get("id"))
            if image_run_id:
                image_run_ids.append(image_run_id)
            output_urls.append(stored_output_url)
            material_asset_ids.append(string_value(image_material.get("id")))
            latest_image_run = image_run
            latest_output_url = stored_output_url

        self._put_execution_context(task, "latestImageRunId", string_value(latest_image_run.get("id")))
        self._put_execution_context(task, "latestImageRunIds", image_run_ids)
        self._put_execution_context(task, "latestImageOutputUrl", latest_output_url)
        self._put_execution_context(task, "latestImageOutputUrls", output_urls)
        self._put_execution_context(task, "latestMaterialAssetId", material_asset_ids[-1] if material_asset_ids else "")
        self._put_execution_context(task, "latestMaterialAssetIds", material_asset_ids)
        await self._task_repository.save(task)
        await self._save_result(
            self._status_stage_service.record_stage_run(
                task,
                run_context,
                1,
                _TaskStage.RENDER,
                1,
                {
                    "title": task.title,
                    "taskType": task.task_type,
                    "width": dimensions[0],
                    "height": dimensions[1],
                    "outputCount": output_count,
                },
                {
                    "summary": "工作台图片生成完成",
                    "imageRunIds": image_run_ids,
                    "outputUrls": output_urls,
                    "materialAssetIds": material_asset_ids,
                },
            )
        )
        await self._save_result(
            self._status_stage_service.complete_workspace_image_task(
                task,
                run_context,
                latest_image_run,
                latest_output_url,
                output_count=output_count,
                image_run_ids=image_run_ids,
            )
        )

    def _is_video_generation_task(self, task: TaskRecord) -> bool:
        return task.task_type is None or task.task_type == "video_generation"

    def _existing_video_clip_indices(self, task: TaskRecord) -> list[int]:
        return existing_video_clip_indices(task.outputs)

    def _last_contiguous_completed_clip_index(self, clip_indices: list[int]) -> int:
        return last_contiguous_completed_clip_index(clip_indices)

    def _resolve_resume_last_frame_url(self, task: TaskRecord, completed_clip_count: int) -> str:
        return resolve_resume_last_frame_url(task.outputs, completed_clip_count, task.execution_context)

    def _build_storyboard_clip_context(
        self, shot_plans: list, clip_duration_plan: list[list[int]]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, shot_plan in enumerate(shot_plans):
            duration = clip_duration_plan[index] if index < len(clip_duration_plan) else [0, 0, 0]
            row: dict[str, Any] = {
                "clipIndex": shot_plan.sequential_index(),
                "shotLabel": shot_plan.shot_label(),
                "scene": shot_plan.scene(),
                "startFramePrompt": shot_plan.first_frame_prompt(),
                "endFramePrompt": shot_plan.last_frame_prompt(),
                "firstFramePrompt": shot_plan.first_frame_prompt(),
                "lastFramePrompt": shot_plan.last_frame_prompt(),
                "actionPath": shot_plan.motion(),
                "motion": shot_plan.motion(),
                "cameraMovement": shot_plan.camera_movement(),
                "durationHint": shot_plan.duration_hint(),
                "imagePrompt": shot_plan.image_prompt(),
                "videoPrompt": shot_plan.video_prompt(),
                "targetDurationSeconds": duration[0],
                "minDurationSeconds": duration[1],
                "maxDurationSeconds": duration[2],
                "continuityRule": "current_end_frame_matches_next_start_frame",
            }
            if index + 1 < len(shot_plans):
                next_shot = shot_plans[index + 1]
                row["nextClipIndex"] = next_shot.sequential_index()
                row["nextClipShotLabel"] = next_shot.shot_label()
                row["nextClipStartFramePrompt"] = next_shot.first_frame_prompt()
            rows.append(row)
        return rows

    def _build_character_definition_context(self, character_definitions: list[Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, character in enumerate(character_definitions, start=1):
            rows.append(
                {
                    "characterIndex": index,
                    "name": string_value(getattr(character, "name", "")),
                    "appearance": string_value(getattr(character, "appearance", "")),
                    "definition": string_value(getattr(character, "definition", "")),
                }
            )
        return rows

    def _put_execution_context(self, task: TaskRecord, key: str, value: Any) -> None:
        if task.execution_context is None:
            task.execution_context = {}
        if value is None:
            task.execution_context.pop(key, None)
            return
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                task.execution_context.pop(key, None)
                return
        task.execution_context[key] = value

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}


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
