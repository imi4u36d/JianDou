"""Task render-stage orchestration service."""

from __future__ import annotations

import re
from typing import Any, Protocol

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
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
)
from backend.services.task_worker_status_stage_service import TaskStage as _TaskStage
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService
from backend.shared import first_non_blank, map_value, safe_int, string_value

_MAX_CHARACTER_REFERENCE_IMAGES = 3
_MAX_CHARACTER_REFERENCE_IMAGES_WITH_SCENE = 2


class GenerationApplicationServiceProtocol(Protocol):
    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]: ...


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
                task,
                clip_index,
                build_clip_frame_context(
                    shot_plan, clip_index, clip_duration_seconds, start_frame, end_frame, "", "", "", ""
                ),
            )
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

            task.progress = min(95, 45 + int(45.0 * clip_index / max(1, len(request.shot_plans))))
            task.completed_output_count = max(task.completed_output_count, clip_index)
            previous_clip_last_frame_url = end_frame.material_url()
            self._put_execution_context(task, "lastFrameUrl", end_frame.material_url())
            self._put_execution_context(task, "lastFrameSourceType", end_frame.source_type())
            self._put_execution_context(task, "lastFrameSourceUrl", end_frame.source_url())
            await self._task_repository.save(task) if self._task_repository else None

        self._runtime_support.assert_task_still_active(task)
        self._put_execution_context(
            task,
            "clipImageRunIds",
            self._merge_string_list_context(task.execution_context.get("clipImageRunIds"), image_run_ids),
        )
        self._put_execution_context(task, "clipVideoRunIds", [])
        self._put_execution_context(task, "videoRunId", None)
        self._put_execution_context(task, "videoOutputUrl", None)
        self._put_execution_context(task, "videoThumbnailUrl", None)
        self._put_execution_context(task, "videoRemoteTaskId", None)
        self._put_execution_context(task, "videoRemoteSourceUrl", None)
        task.completed_output_count = len(request.shot_plans)
        self._put_execution_context(task, "resumeExistingOutputCount", None)
        self._put_execution_context(task, "resumeExistingClipIndices", None)
        self._put_execution_context(task, "resumeRenderFromClipIndex", None)
        self._put_execution_context(task, "attemptResumeFromStage", None)
        self._put_execution_context(task, "attemptResumeFromClipIndex", None)
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
        image_request = self._runtime_support.build_image_run_request(
            task,
            clip_index,
            prompt,
            width,
            height,
            reference_image_url,
            duration_seconds,
            frame_role,
            reference_image_urls=reference_image_urls,
        )
        pending_image_model_call = self._status_stage_service.create_pending_model_call(
            task,
            _TaskStage.PLANNING,
            "generation.image",
            image_request,
            clip_index,
            f"{_GenerationModelKinds.IMAGE}.{frame_role}",
        )
        await self._save_result(self._execution_coordinator.record_model_call(task, pending_image_model_call))
        try:
            image_run = await self._generation_application_service.create_run(image_request)
        except Exception as ex:
            await self._save_result(
                self._execution_coordinator.record_model_call(
                    task, self._status_stage_service.fail_model_call(pending_image_model_call, ex)
                )
            )
            raise
        self._runtime_support.assert_task_still_active(task)
        image_result = self._result_map(image_run)
        image_metadata = map_value(image_result.get("metadata"))
        keyframe_source_url = first_non_blank(
            string_value(image_result.get("outputUrl")),
            string_value(image_metadata.get("remoteSourceUrl")),
        )
        image_model_call = self._status_stage_service.complete_model_call(
            pending_image_model_call, image_run, image_result
        )
        await self._save_result(self._execution_coordinator.record_model_call(task, image_model_call))
        self._status_stage_service.record_run_call_chain(task, _TaskStage.PLANNING, image_run, image_result)
        image_material = self._artifact_assembler.create_image_material(
            task, image_run, image_result, clip_index, frame_role
        )
        await self._save_result(self._execution_coordinator.record_material(task, image_material))
        material_url = string_value(image_material.get("fileUrl"))
        image_run_ids.append(string_value(image_run.get("id")))
        return FrameResolution(
            prompt_value=string_value(prompt),
            frame_role_value=string_value(frame_role),
            source_type_value=string_value(source_type),
            source_url_value=first_non_blank(material_url, keyframe_source_url),
            material_url_value=material_url,
            remote_url_value=first_non_blank(string_value(image_material.get("remoteUrl")), keyframe_source_url),
            video_input_url_value=first_non_blank(
                material_url, keyframe_source_url, string_value(image_material.get("remoteUrl"))
            ),
            run_id_value=string_value(image_run.get("id")),
            material_value=image_material,
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
        """Generate missing character reference sheets and reuse stored sheets during resume."""
        if not character_definitions:
            self._put_execution_context(task, "characterSheetUrls", [])
            return []

        existing = self._existing_character_sheet_urls(task)
        resolved_urls: list[str] = []
        generated_count = 0
        reused_count = 0

        await self._save_result(
            self._execution_coordinator.record_trace(
                task,
                _TaskStage.PLANNING,
                "planning.character_sheets_started",
                "任务开始生成角色三视图设定图。",
                "INFO",
                {"characterCount": len(character_definitions)},
            )
        )

        for index, character in enumerate(character_definitions, start=1):
            existing_url = existing.get(index, "")
            if existing_url:
                resolved_urls.append(existing_url)
                reused_count += 1
                continue

            sheet_request = self._runtime_support.build_character_sheet_run_request(
                task,
                index,
                character,
                width,
                height,
            )
            pending_model_call = self._status_stage_service.create_pending_model_call(
                task,
                _TaskStage.PLANNING,
                "generation.image",
                sheet_request,
                1000 + index,
                "image.character_sheet",
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, pending_model_call))
            try:
                sheet_run = await self._generation_application_service.create_run(sheet_request)
            except Exception as ex:
                await self._save_result(
                    self._execution_coordinator.record_model_call(
                        task,
                        self._status_stage_service.fail_model_call(pending_model_call, ex),
                    )
                )
                raise

            self._runtime_support.assert_task_still_active(task)
            sheet_result = self._result_map(sheet_run)
            sheet_metadata = map_value(sheet_result.get("metadata"))
            sheet_url = first_non_blank(
                string_value(sheet_metadata.get("remoteSourceUrl")),
                string_value(sheet_result.get("outputUrl")),
            )
            if not sheet_url:
                raise ValueError(f"角色 {index} 三视图生成结果为空，未返回可用输出地址。")

            sheet_model_call = self._status_stage_service.complete_model_call(
                pending_model_call, sheet_run, sheet_result
            )
            await self._save_result(self._execution_coordinator.record_model_call(task, sheet_model_call))
            self._status_stage_service.record_run_call_chain(task, _TaskStage.PLANNING, sheet_run, sheet_result)
            sheet_material = self._artifact_assembler.create_character_sheet_material(
                task,
                sheet_run,
                sheet_result,
                index,
                character,
            )
            await self._save_result(self._execution_coordinator.record_material(task, sheet_material))
            stored_sheet_url = first_non_blank(
                string_value(sheet_material.get("fileUrl")),
                sheet_url,
                string_value(sheet_material.get("remoteUrl")),
            )
            resolved_urls.append(stored_sheet_url)
            image_run_id = string_value(sheet_run.get("id"))
            if image_run_id:
                image_run_ids.append(image_run_id)
            generated_count += 1

            await self._save_result(
                self._status_stage_service.record_stage_run(
                    task,
                    run_context,
                    50 + index,
                    _TaskStage.PLANNING,
                    1000 + index,
                    {
                        "variantKind": "character_sheet",
                        "characterIndex": index,
                        "characterName": string_value(getattr(character, "name", "")),
                        "width": width,
                        "height": height,
                    },
                    {
                        "summary": "角色三视图设定图已生成",
                        "sheetUrl": stored_sheet_url,
                        "imageRunId": image_run_id,
                    },
                )
            )

        self._put_execution_context(task, "characterSheetUrls", resolved_urls)
        self._put_execution_context(task, "characterSheetCount", len(resolved_urls))
        await self._task_repository.save(task) if self._task_repository else None
        await self._save_result(
            self._execution_coordinator.record_trace(
                task,
                _TaskStage.PLANNING,
                "planning.character_sheets_resolved",
                "角色三视图设定图已就绪。",
                "INFO",
                {
                    "characterCount": len(character_definitions),
                    "sheetCount": len(resolved_urls),
                    "generatedCount": generated_count,
                    "reusedCount": reused_count,
                    "sheetUrls": resolved_urls,
                },
            )
        )
        return resolved_urls

    def _frame_reference_image_urls(
        self,
        prompt: str,
        scene_reference_url: str,
        character_sheet_urls: list[str],
        character_definitions: list[Any],
    ) -> list[str]:
        """Build the provider reference image list without exceeding model payload limits."""
        references: list[str] = []
        normalized_scene_reference_url = string_value(scene_reference_url)
        if normalized_scene_reference_url:
            references.append(normalized_scene_reference_url)

        if not character_sheet_urls:
            return references

        max_character_references = (
            _MAX_CHARACTER_REFERENCE_IMAGES_WITH_SCENE
            if normalized_scene_reference_url
            else _MAX_CHARACTER_REFERENCE_IMAGES
        )
        selected_indexes = self._matching_character_indexes(prompt, character_definitions, len(character_sheet_urls))
        if not selected_indexes:
            selected_indexes = list(range(1, len(character_sheet_urls) + 1))

        for index in selected_indexes:
            if len(references) >= max_character_references + (1 if normalized_scene_reference_url else 0):
                break
            if index < 1 or index > len(character_sheet_urls):
                continue
            url = string_value(character_sheet_urls[index - 1])
            if url and url not in references:
                references.append(url)
        return references

    def _matching_character_indexes(self, prompt: str, character_definitions: list[Any], sheet_count: int) -> list[int]:
        normalized_prompt = string_value(prompt)
        if not normalized_prompt:
            return []
        lowered_prompt = normalized_prompt.lower()
        matches: list[tuple[int, int]] = []
        for index, character in enumerate(character_definitions[:sheet_count], start=1):
            name = string_value(getattr(character, "name", ""))
            if not name:
                continue
            position = self._character_name_position(normalized_prompt, lowered_prompt, name)
            if position >= 0:
                matches.append((position, index))
        matches.sort(key=lambda item: item[0])
        return [index for _, index in matches]

    @staticmethod
    def _character_name_position(prompt: str, lowered_prompt: str, name: str) -> int:
        normalized_name = string_value(name)
        if not normalized_name:
            return -1
        direct_position = prompt.find(normalized_name)
        if direct_position >= 0:
            return direct_position
        lowered_name = normalized_name.lower()
        if re.search(r"[A-Za-z0-9_]", lowered_name):
            match = re.search(rf"(?<![A-Za-z0-9_]){re.escape(lowered_name)}(?![A-Za-z0-9_])", lowered_prompt)
            return match.start() if match else -1
        return -1

    def _existing_character_sheet_urls(self, task: TaskRecord) -> dict[int, str]:
        """Return previously materialized character sheets keyed by one-based character index."""
        resolved: dict[int, str] = {}
        for material in task.materials:
            if string_value(material.get("kind", material.get("assetRole", ""))) != "character_sheet":
                continue
            metadata = map_value(material.get("metadata"))
            index = safe_int(metadata.get("characterIndex"), 0)
            if index <= 0:
                clip_index = safe_int(material.get("clipIndex"), 0)
                index = clip_index - 1000 if clip_index > 1000 else 0
            url = first_non_blank(
                string_value(material.get("fileUrl")),
                string_value(material.get("previewUrl")),
                string_value(material.get("remoteUrl")),
            )
            if index > 0 and url.startswith("/storage/"):
                resolved[index] = url
        return resolved

    async def _reuse_frame(
        self, task: TaskRecord, clip_index: int, source_url: str, frame_role: str, source_type: str
    ) -> FrameResolution:
        image_material = self._artifact_assembler.create_reference_frame_material(
            task, clip_index, source_url, frame_role
        )
        await self._save_result(self._execution_coordinator.record_material(task, image_material))
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

    def _put_clip_frame_execution_context(
        self, task: TaskRecord, clip_index: int, clip_frame_context: dict[str, Any]
    ) -> None:
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
