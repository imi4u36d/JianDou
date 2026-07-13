"""Prepare storyboard analysis and normalized render plans for task workers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_worker_pipeline_context import (
    build_character_definition_context,
    build_storyboard_clip_context,
    generation_result_map,
    put_execution_context,
)
from backend.services.task_worker_status_stage_service import (
    TaskStage,
    TaskWorkerExecutionContext,
    TaskWorkerStatusStageService,
)
from backend.shared import string_value


@dataclass(slots=True)
class StoryboardPreparationResult:
    script_run: dict[str, Any]
    shot_plans: list[Any]
    character_definitions: list[Any]
    clip_duration_plan: list[list[int]]


class TaskStoryboardPreparationService:
    """Own script generation/reuse, storyboard parsing, and planning persistence."""

    def __init__(
        self,
        task_repository: TaskRepository,
        generation_service: Any,
        runtime_support: TaskExecutionRuntimeSupport,
        artifact_assembler: TaskExecutionArtifactAssembler,
        storyboard_planner: Any,
        status_stage_service: TaskWorkerStatusStageService,
        execution_coordinator: TaskExecutionCoordinator,
        save_result: Callable[[dict[str, Any] | None], Awaitable[None]],
    ) -> None:
        self._task_repository = task_repository
        self._generation_service = generation_service
        self._runtime_support = runtime_support
        self._artifact_assembler = artifact_assembler
        self._storyboard_planner = storyboard_planner
        self._status_stage_service = status_stage_service
        self._execution_coordinator = execution_coordinator
        self._save_result = save_result

    async def prepare(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        *,
        duration_seconds: int,
        reuse_storyboard: bool,
        completed_clip_count: int,
        render_start_index: int,
        requested_resume_stage: str,
        requested_resume_clip_index: int,
    ) -> StoryboardPreparationResult:
        script_run: dict[str, Any] = {}
        storyboard_markdown = ""
        if reuse_storyboard and task.storyboard_script and task.storyboard_script.strip():
            storyboard_markdown = task.storyboard_script
            await self._save_result(
                self._execution_coordinator.record_trace(
                    task,
                    TaskStage.ANALYSIS,
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
            script_run, storyboard_markdown = await self._generate_storyboard(task, run_context)

        shot_plans = self._storyboard_planner.build_storyboard_shot_plans(task, storyboard_markdown)
        character_definitions = self._storyboard_planner.extract_character_definitions(storyboard_markdown)
        storyboard_clip_count = len(shot_plans)
        requested_output_count = self._storyboard_planner.resolve_requested_output_count(
            task,
            storyboard_clip_count,
        )
        if requested_output_count < len(shot_plans):
            shot_plans = list(shot_plans[:requested_output_count])
        clip_prompts = [shot_plan.video_prompt() for shot_plan in shot_plans]
        duration_ranges = self._storyboard_planner.extract_storyboard_shot_duration_ranges(storyboard_markdown)
        clip_duration_plan = self._storyboard_planner.build_clip_duration_plan(
            task,
            duration_seconds,
            len(clip_prompts),
            storyboard_markdown,
        )
        snapshot = task.request_snapshot or {}
        clip_duration_plan = self._storyboard_planner.normalize_clip_duration_plan(
            string_value(snapshot.get("videoModel", "")),
            clip_duration_plan,
        )
        put_execution_context(task, "storyboardClipCount", storyboard_clip_count)
        put_execution_context(
            task,
            "requestedOutputCount",
            self._storyboard_planner.request_snapshot_output_count(task),
        )
        put_execution_context(task, "plannedClipCount", len(clip_prompts))
        put_execution_context(task, "characterDefinitionCount", len(character_definitions))
        put_execution_context(task, "characterDefinitions", build_character_definition_context(character_definitions))
        put_execution_context(task, "clipPrompts", clip_prompts)
        put_execution_context(
            task,
            "clipDurationPlan",
            self._storyboard_planner.build_clip_duration_plan_context(clip_duration_plan, duration_ranges),
        )
        put_execution_context(task, "storyboardFormatVersion", "structured-md-v1")
        put_execution_context(task, "storyboardContinuityRule", "current_end_frame_matches_next_start_frame")
        put_execution_context(task, "storyboardClips", build_storyboard_clip_context(shot_plans, clip_duration_plan))
        await self._task_repository.save(task)

        await self._save_result(
            self._execution_coordinator.record_trace(
                task,
                TaskStage.PLANNING,
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
                TaskStage.PLANNING,
                "task.planning",
                "任务开始按分镜生成关键画面。",
            )
        )
        return StoryboardPreparationResult(
            script_run,
            list(shot_plans),
            list(character_definitions),
            clip_duration_plan,
        )

    async def _generate_storyboard(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
    ) -> tuple[dict[str, Any], str]:
        await self._save_result(
            self._status_stage_service.update_status(
                task,
                run_context,
                "ANALYZING",
                10,
                TaskStage.ANALYSIS,
                "task.analyzing",
                "任务开始分析文本与镜头约束。",
            )
        )
        script_request = self._runtime_support.build_script_run_request(task)
        pending_call = self._status_stage_service.create_pending_model_call(
            task,
            TaskStage.ANALYSIS,
            "generation.script",
            script_request,
            1,
            "script",
        )
        await self._save_result(self._execution_coordinator.record_model_call(task, pending_call))
        try:
            script_run = await self._generation_service.create_run(script_request)
        except Exception as error:
            failed_call = self._status_stage_service.fail_model_call(pending_call, error)
            await self._save_result(self._execution_coordinator.record_model_call(task, failed_call))
            raise
        self._runtime_support.assert_task_still_active(task)
        script_result = generation_result_map(script_run)
        storyboard_markdown = string_value(script_result.get("scriptMarkdown"))
        if not storyboard_markdown:
            raise ValueError("分镜脚本为空，未生成有效输出。")
        task.storyboard_script = storyboard_markdown
        put_execution_context(task, "analysisRunId", string_value(script_run.get("id")))
        put_execution_context(task, "scriptRunId", string_value(script_run.get("id")))
        put_execution_context(task, "analysisScriptText", storyboard_markdown)
        put_execution_context(task, "analysisPrompt", string_value(script_result.get("prompt")))
        await self._task_repository.save(task)
        await self._save_result(
            self._status_stage_service.record_stage_run(
                task,
                run_context,
                1,
                TaskStage.ANALYSIS,
                1,
                {"title": task.title, "aspectRatio": task.aspect_ratio},
                {"summary": "文本分析完成", "scriptRunId": string_value(script_run.get("id"))},
            )
        )
        completed_call = self._status_stage_service.complete_model_call(pending_call, script_run, script_result)
        await self._save_result(self._execution_coordinator.record_model_call(task, completed_call))
        self._status_stage_service.record_run_call_chain(task, TaskStage.ANALYSIS, script_run, script_result)
        script_material = self._artifact_assembler.create_text_material(task, script_run, script_result)
        await self._save_result(self._execution_coordinator.record_material(task, script_material))
        put_execution_context(task, "storyboardFileUrl", string_value(script_material.get("fileUrl")))
        await self._task_repository.save(task)
        return script_run, storyboard_markdown
