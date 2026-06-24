"""Task render-stage orchestration service."""

from __future__ import annotations

from typing import Any, Protocol

from backend.domain.media_artifacts import (
    file_ext_or_default as artifact_file_ext_or_default,
)
from backend.domain.media_artifacts import (
    file_name_from_url as artifact_file_name_from_url,
)
from backend.domain.task_record import TaskRecord
from backend.domain.task_result_types import is_primary_video
from backend.domain.video_run_monitor import (
    assert_video_run_succeeded,
    is_video_run_active,
    normalized_video_run_status,
)
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler, _TaskArtifactNaming
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import GenerationModelKinds as _GenerationModelKinds
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_render_stage_payloads import (
    FrameResolution,
    RenderStageRequest,
    RenderStageResult,
    build_clip_frame_context,
    build_frame_continuity_prompt,
    build_planning_stage_request,
    build_planning_stage_response,
    build_render_stage_request,
    build_render_stage_response,
)
from backend.services.task_render_stage_payloads import (
    resolved_last_frame_source_type as resolve_last_frame_source_type,
)
from backend.services.task_render_stage_payloads import (
    resolved_last_frame_source_url as resolve_last_frame_source_url,
)
from backend.services.task_worker_status_stage_service import TaskStage as _TaskStage
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService
from backend.shared import first_non_blank, map_value, safe_int, string_value


class GenerationApplicationServiceProtocol(Protocol):
    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]: ...

    async def get_run(self, run_id: str) -> dict[str, Any]: ...

class JoinStageServiceProtocol(Protocol):
    def schedule_join(self, task_id: str, end_clip_index: int) -> None: ...

class TaskWorkerRenderStageService:
    """Handles the render stage of task execution — keyframe generation and clip rendering."""

    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        execution_coordinator: TaskExecutionCoordinator | None = None,
        generation_application_service: GenerationApplicationServiceProtocol | None = None,
        runtime_support: TaskExecutionRuntimeSupport | None = None,
        artifact_assembler: TaskExecutionArtifactAssembler | None = None,
        status_stage_service: TaskWorkerStatusStageService | None = None,
        join_stage_service: JoinStageServiceProtocol | None = None,
        video_run_poll_interval_ms: int = 1000,
        video_run_max_polls: int = 240,
    ) -> None:
        self._task_repository = task_repository
        self._execution_coordinator = execution_coordinator or TaskExecutionCoordinator()
        if generation_application_service is None:
            raise RuntimeError("generation application service not configured")
        self._generation_application_service = generation_application_service
        self._runtime_support = runtime_support or TaskExecutionRuntimeSupport()
        self._artifact_assembler = artifact_assembler or TaskExecutionArtifactAssembler()
        self._status_stage_service = status_stage_service or TaskWorkerStatusStageService(
            task_repository=task_repository, execution_coordinator=self._execution_coordinator,
        )
        self._join_stage_service = join_stage_service
        self._video_run_poll_interval_ms = max(0, video_run_poll_interval_ms)
        self._video_run_max_polls = max(1, video_run_max_polls)

    async def render(self, task: TaskRecord, run_context: TaskWorkerExecutionContext, request: RenderStageRequest) -> RenderStageResult:
        image_run_ids: list[str] = []
        video_run_ids: list[str] = []
        previous_clip_last_frame_url = request.previous_clip_last_frame_url
        latest_video_output_url = ""

        if request.reuse_storyboard and request.render_start_index > 1:
            self._execution_coordinator.record_trace(
                task, _TaskStage.PLANNING, "planning.keyframe_reused_for_resume",
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

        for index in range(max(0, request.render_start_index - 1), len(request.shot_plans)):
            self._runtime_support.assert_task_still_active(task)
            clip_index = index + 1
            shot_plan = request.shot_plans[index]

            clip_prompt = shot_plan.video_prompt()
            first_frame_prompt = first_non_blank(
                getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
                getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
                clip_prompt,
            )
            last_frame_prompt = first_non_blank(
                getattr(shot_plan, 'last_frame_prompt', lambda: "")(),
                getattr(shot_plan, 'first_frame_prompt', lambda: "")(),
                clip_prompt,
            )

            clip_duration = request.clip_duration_plan[index] if index < len(request.clip_duration_plan) else [0, 0, 0]
            clip_duration_seconds = clip_duration[0]
            clip_min_duration = clip_duration[1]
            clip_max_duration = clip_duration[2]

            reuse_previous_last_frame = clip_index > 1
            if reuse_previous_last_frame:
                if not previous_clip_last_frame_url.strip():
                    raise ValueError(f"clip {clip_index} requires previous clip last frame before generating its end frame")
                start_frame = self._reuse_frame(task, clip_index, previous_clip_last_frame_url, "first", "previous_video_last_frame")
                self._execution_coordinator.record_trace(
                    task, _TaskStage.PLANNING, "planning.keyframe_reused_from_last_frame",
                    "复用上一镜尾帧作为当前镜头首帧。", "INFO",
                    {"clipIndex": clip_index, "firstFrameUrl": start_frame.video_input_url(), "sourceLastFrameUrl": previous_clip_last_frame_url},
                )
            else:
                start_frame = await self._generate_frame(
                    task, clip_index, first_frame_prompt, request.width, request.height,
                    previous_clip_last_frame_url, clip_duration_seconds, "first",
                    "generated_start_frame_keyframe" if clip_index == 1 else "generated_start_frame_keyframe_fallback",
                    image_run_ids,
                )

            continuity_prompt = build_frame_continuity_prompt(
                shot_plan, last_frame_prompt, start_frame.prompt(), start_frame.video_input_url(), "last",
            )
            end_frame = await self._generate_frame(
                task, clip_index, continuity_prompt, request.width, request.height,
                start_frame.video_input_url(), clip_duration_seconds, "last",
                "generated_end_frame_keyframe", image_run_ids,
            )

            self._put_execution_context(task, "imageRunId", first_non_blank(start_frame.run_id(), end_frame.run_id()))
            self._put_execution_context(task, "keyframeOutputUrl", start_frame.material_url())
            self._put_execution_context(task, "keyframeRemoteSourceUrl", start_frame.source_url())
            self._put_execution_context(task, "firstFrameUrl", start_frame.video_input_url())
            self._put_execution_context(task, "startFrameUrl", start_frame.video_input_url())
            self._put_execution_context(task, "startFrameSourceType", start_frame.source_type())
            self._put_execution_context(task, "startFrameSourceUrl", start_frame.source_url())
            self._put_execution_context(task, "startFrameKeyframeUrl", start_frame.material_url())
            self._put_execution_context(task, "startFrameKeyframeRemoteSourceUrl", start_frame.remote_url())
            self._put_execution_context(task, "startFrameKeyframeRunId", start_frame.run_id())
            self._put_execution_context(task, "lastFrameImageRunId", end_frame.run_id())
            self._put_execution_context(task, "requestedLastFrameUrl", end_frame.video_input_url())
            self._put_execution_context(task, "endFrameConstraintUrl", end_frame.video_input_url())
            self._put_execution_context(task, "endFrameConstraintSourceType", end_frame.source_type())
            self._put_execution_context(task, "endFrameConstraintSourceUrl", end_frame.source_url())
            self._put_execution_context(task, "endFrameKeyframeUrl", end_frame.material_url())
            self._put_execution_context(task, "endFrameKeyframeRemoteSourceUrl", end_frame.remote_url())
            self._put_execution_context(task, "endFrameKeyframeRunId", end_frame.run_id())
            self._put_clip_frame_execution_context(
                task, clip_index,
                build_clip_frame_context(shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame, "", "", "", ""),
            )
            await self._task_repository.save(task) if self._task_repository else None

            self._execution_coordinator.record_trace(
                task, _TaskStage.PLANNING, "planning.clip_frames_resolved",
                "当前分镜首尾帧约束已就绪。", "INFO",
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
            self._status_stage_service.record_stage_run(
                task, run_context,
                100 + clip_index, _TaskStage.PLANNING, clip_index,
                build_planning_stage_request(task, clip_prompt, first_frame_prompt, last_frame_prompt, clip_duration_seconds),
                build_planning_stage_response(start_frame, end_frame, reuse_previous_last_frame),
            )

            if index == max(0, request.render_start_index - 1):
                self._status_stage_service.update_status(task, run_context, "RENDERING", 55, _TaskStage.RENDER, "task.rendering", "任务开始按分镜生成视频输出。")
            else:
                task.progress = min(94, 55 + int(35.0 * index / max(1, len(request.shot_plans))))
                await self._task_repository.save(task) if self._task_repository else None

            video_request = self._runtime_support.build_video_run_request(
                task, clip_index, clip_prompt, request.video_size,
                clip_duration_seconds, clip_min_duration, clip_max_duration,
                start_frame.video_input_url(), end_frame.video_input_url(),
            )
            pending_video_model_call = self._status_stage_service.create_pending_model_call(
                task, _TaskStage.RENDER, "generation.video", video_request, clip_index, _GenerationModelKinds.VIDEO,
            )
            self._execution_coordinator.record_model_call(task, pending_video_model_call)

            try:
                video_run = await self._generation_application_service.create_run(video_request)
            except Exception as ex:
                self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_video_model_call, ex))
                raise

            video_run = await self._await_completed_video_run(video_run)
            self._runtime_support.assert_task_still_active(task)

            video_result = self._result_map(video_run)
            video_metadata = map_value(video_result.get("metadata"))
            extracted_last_frame_url = self._artifact_assembler.extract_last_frame_url(video_result)
            provider_requested_last_frame_url = string_value(video_metadata.get("requestedLastFrameUrl"))

            resolved_first_frame_url = first_non_blank(
                string_value(video_metadata.get("firstFrameUrl")), start_frame.video_input_url(),
            )
            resolved_last_frame_url = first_non_blank(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )
            resolved_last_frame_source_type = resolve_last_frame_source_type(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )
            resolved_last_frame_source_url = resolve_last_frame_source_url(
                extracted_last_frame_url, provider_requested_last_frame_url, end_frame.video_input_url(),
            )

            self._artifact_assembler.normalize_optional_task_artifact(
                task, resolved_last_frame_url,
                _TaskArtifactNaming.last_frame_file_name(clip_index, _file_ext_or_default(_file_name_from_url(resolved_last_frame_url), "png")),
            )

            self._put_execution_context(task, "videoRunId", string_value(video_run.get("id")))
            self._put_execution_context(task, "videoOutputUrl", string_value(video_result.get("outputUrl")))
            self._put_execution_context(task, "videoThumbnailUrl", string_value(video_result.get("thumbnailUrl")))
            self._put_execution_context(task, "firstFrameUrl", resolved_first_frame_url)
            self._put_execution_context(task, "startFrameUrl", resolved_first_frame_url)
            self._put_execution_context(task, "lastFrameUrl", resolved_last_frame_url)
            self._put_execution_context(task, "lastFrameSourceType", resolved_last_frame_source_type)
            self._put_execution_context(task, "lastFrameSourceUrl", resolved_last_frame_source_url)
            self._put_execution_context(task, "requestedLastFrameUrl", end_frame.video_input_url())
            self._put_execution_context(task, "videoRemoteTaskId", string_value(video_metadata.get("taskId")))
            self._put_execution_context(task, "videoRemoteSourceUrl", string_value(video_metadata.get("remoteSourceUrl")))
            self._put_clip_frame_execution_context(
                task, clip_index,
                build_clip_frame_context(
                    shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame,
                    string_value(video_run.get("id")),
                    first_non_blank(string_value(video_result.get("outputUrl")), string_value(video_metadata.get("remoteSourceUrl"))),
                    resolved_last_frame_url, resolved_last_frame_source_type,
                ),
            )
            await self._task_repository.save(task) if self._task_repository else None

            video_model_call = self._status_stage_service.complete_model_call(pending_video_model_call, video_run, video_result)
            self._execution_coordinator.record_model_call(task, video_model_call)
            self._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, video_run, video_result)

            video_material = self._artifact_assembler.create_video_material(task, video_run, video_result, clip_index, clip_duration_seconds)
            self._execution_coordinator.record_material(task, video_material)

            self._put_execution_context(task, "videoOutputUrl", string_value(video_material.get("fileUrl")))
            self._put_clip_frame_execution_context(
                task, clip_index,
                build_clip_frame_context(
                    shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame,
                    string_value(video_run.get("id")),
                    string_value(video_material.get("fileUrl")),
                    resolved_last_frame_url, resolved_last_frame_source_type,
                ),
            )
            latest_video_output_url = string_value(video_material.get("fileUrl"))
            task.completed_output_count = max(task.completed_output_count, clip_index)
            await self._task_repository.save(task) if self._task_repository else None

            video_output = self._artifact_assembler.create_result(
                task, video_run, video_result, video_material, start_frame.material(),
                video_model_call, resolved_last_frame_url, clip_index,
                clip_duration_seconds, clip_min_duration, clip_max_duration,
            )
            self._execution_coordinator.record_result(task, video_output)

            self._status_stage_service.record_stage_run(
                task, run_context,
                200 + clip_index, _TaskStage.RENDER, clip_index,
                build_render_stage_request(start_frame, end_frame, clip_duration_seconds),
                build_render_stage_response(
                    video_run, video_material, video_metadata,
                    resolved_first_frame_url, resolved_last_frame_url, resolved_last_frame_source_type,
                    end_frame.video_input_url(),
                ),
            )
            self._execution_coordinator.record_trace(
                task, _TaskStage.RENDER, "render.clip_completed",
                "当前分镜片段已生成完成。", "INFO",
                {
                    "clipIndex": clip_index,
                    "clipCount": len(request.shot_plans),
                    "outputUrl": string_value(video_material.get("fileUrl")),
                    "firstFrameUrl": resolved_first_frame_url,
                    "firstFrameSourceType": start_frame.source_type(),
                    "requestedLastFrameUrl": end_frame.video_input_url(),
                    "requestedLastFrameSourceType": end_frame.source_type(),
                    "lastFrameUrl": resolved_last_frame_url,
                    "lastFrameSourceType": resolved_last_frame_source_type,
                },
            )
            video_run_ids.append(string_value(video_run.get("id")))
            previous_clip_last_frame_url = resolved_last_frame_url
            if self._join_stage_service:
                self._join_stage_service.schedule_join(task.id, clip_index)

        self._runtime_support.assert_task_still_active(task)
        if not latest_video_output_url:
            latest_video_output_url = self._resolve_latest_video_output_url(task)
        if self._join_stage_service:
            self._join_stage_service.schedule_join(task.id, len(request.shot_plans))
        self._put_execution_context(task, "clipImageRunIds", self._merge_string_list_context(task.execution_context.get("clipImageRunIds"), image_run_ids))
        self._put_execution_context(task, "clipVideoRunIds", self._merge_string_list_context(task.execution_context.get("clipVideoRunIds"), video_run_ids))
        task.completed_output_count = len(request.shot_plans)
        self._put_execution_context(task, "resumeExistingOutputCount", None)
        self._put_execution_context(task, "resumeExistingClipIndices", None)
        self._put_execution_context(task, "resumeRenderFromClipIndex", None)
        self._put_execution_context(task, "attemptResumeFromStage", None)
        self._put_execution_context(task, "attemptResumeFromClipIndex", None)
        await self._task_repository.save(task) if self._task_repository else None
        return RenderStageResult(image_run_ids, video_run_ids, latest_video_output_url, len(request.shot_plans))

    async def _await_completed_video_run(self, initial_run: dict[str, Any]) -> dict[str, Any]:
        current_status = normalized_video_run_status(initial_run)
        if not is_video_run_active(current_status):
            assert_video_run_succeeded(initial_run, current_status)
            return initial_run
        run_id = string_value(initial_run.get("id"))
        if not run_id:
            raise ValueError("video run is active but missing run id")
        current_run = initial_run
        for _ in range(self._video_run_max_polls):
            current_run = await self._generation_application_service.get_run(run_id)
            current_status = normalized_video_run_status(current_run)
            if not is_video_run_active(current_status):
                assert_video_run_succeeded(current_run, current_status)
                return current_run
            await self._sleep_before_next_video_poll()
        raise TimeoutError(f"video run wait timeout: runId={run_id}, status={current_status}, maxPolls={self._video_run_max_polls}")

    async def _generate_frame(self, task: TaskRecord, clip_index: int, prompt: str, width: int, height: int,
                              reference_image_url: str, duration_seconds: int, frame_role: str,
                              source_type: str, image_run_ids: list[str]) -> FrameResolution:
        image_request = self._runtime_support.build_image_run_request(
            task, clip_index, prompt, width, height, reference_image_url, duration_seconds, frame_role,
        )
        pending_image_model_call = self._status_stage_service.create_pending_model_call(
            task, _TaskStage.PLANNING, "generation.image", image_request, clip_index, _GenerationModelKinds.IMAGE,
        )
        self._execution_coordinator.record_model_call(task, pending_image_model_call)
        try:
            image_run = await self._generation_application_service.create_run(image_request)
        except Exception as ex:
            self._execution_coordinator.record_model_call(task, self._status_stage_service.fail_model_call(pending_image_model_call, ex))
            raise
        self._runtime_support.assert_task_still_active(task)
        image_result = self._result_map(image_run)
        image_metadata = map_value(image_result.get("metadata"))
        keyframe_source_url = first_non_blank(
            string_value(image_metadata.get("remoteSourceUrl")),
            string_value(image_result.get("outputUrl")),
        )
        image_model_call = self._status_stage_service.complete_model_call(pending_image_model_call, image_run, image_result)
        self._execution_coordinator.record_model_call(task, image_model_call)
        self._status_stage_service.record_run_call_chain(task, _TaskStage.PLANNING, image_run, image_result)
        image_material = self._artifact_assembler.create_image_material(task, image_run, image_result, clip_index, frame_role)
        self._execution_coordinator.record_material(task, image_material)
        image_run_ids.append(string_value(image_run.get("id")))
        return FrameResolution(
            prompt_value=string_value(prompt),
            frame_role_value=string_value(frame_role),
            source_type_value=string_value(source_type),
            source_url_value=keyframe_source_url,
            material_url_value=string_value(image_material.get("fileUrl")),
            remote_url_value=first_non_blank(string_value(image_material.get("remoteUrl")), keyframe_source_url),
            video_input_url_value=first_non_blank(keyframe_source_url, string_value(image_material.get("remoteUrl")), string_value(image_material.get("fileUrl"))),
            run_id_value=string_value(image_run.get("id")),
            material_value=image_material,
        )

    def _reuse_frame(self, task: TaskRecord, clip_index: int, source_url: str, frame_role: str, source_type: str) -> FrameResolution:
        image_material = self._artifact_assembler.create_reference_frame_material(task, clip_index, source_url, frame_role)
        self._execution_coordinator.record_material(task, image_material)
        remote_url = first_non_blank(string_value(image_material.get("remoteUrl")), source_url)
        return FrameResolution(
            prompt_value="",
            frame_role_value=string_value(frame_role),
            source_type_value=string_value(source_type),
            source_url_value=string_value(source_url),
            material_url_value=string_value(image_material.get("fileUrl")),
            remote_url_value=remote_url,
            video_input_url_value=first_non_blank(remote_url, string_value(image_material.get("fileUrl"))),
            run_id_value="",
            material_value=image_material,
        )

    def _put_clip_frame_execution_context(self, task: TaskRecord, clip_index: int, clip_frame_context: dict[str, Any]) -> None:
        rows: list[dict[str, Any]] = []
        existing = task.execution_context.get("clipFrameContexts")
        if isinstance(existing, list):
            for item in existing:
                if isinstance(item, dict):
                    if safe_int(item.get("clipIndex"), 0) != clip_index:
                        rows.append(dict(item))
        rows.append(clip_frame_context)
        rows.sort(key=lambda r: safe_int(r.get("clipIndex"), 0))
        self._put_execution_context(task, "clipFrameContexts", rows)

    def _result_map(self, run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}

    def _resolve_latest_video_output_url(self, task: TaskRecord) -> str:
        latest_clip_index = 0
        latest_output_url = ""
        for output in task.outputs:
            if not is_primary_video(output.get("resultType")):
                continue
            clip_index = safe_int(output.get("clipIndex"), 0)
            if clip_index >= latest_clip_index:
                latest_clip_index = clip_index
                latest_output_url = first_non_blank(
                    string_value(output.get("downloadUrl")),
                    string_value(output.get("previewUrl")),
                )
        return latest_output_url

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

    def _merge_string_list_context(self, existing: Any, appended: list[str]) -> list[str]:
        merged: set[str] = set()
        if isinstance(existing, list):
            for item in existing:
                v = string_value(item)
                if v:
                    merged.add(v)
        for item in appended:
            v = string_value(item)
            if v:
                merged.add(v)
        return list(merged)

    async def _sleep_before_next_video_poll(self) -> None:
        if self._video_run_poll_interval_ms <= 0:
            return
        import asyncio
        await asyncio.sleep(self._video_run_poll_interval_ms / 1000.0)

def _file_name_from_url(url: str) -> str:
    return artifact_file_name_from_url(url)

def _file_ext_or_default(file_name: str, fallback: str) -> str:
    return artifact_file_ext_or_default(file_name, fallback)
