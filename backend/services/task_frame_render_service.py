"""Generate and reuse task keyframes with model-call and material recording."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import GenerationModelKinds, TaskExecutionRuntimeSupport
from backend.services.task_render_stage_payloads import FrameResolution
from backend.services.task_worker_status_stage_service import TaskStage, TaskWorkerStatusStageService
from backend.shared import first_non_blank, map_value, string_value


class GenerationApplicationServiceProtocol(Protocol):
    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]: ...


class TaskFrameRenderService:
    """Own individual frame generation and reference-frame reuse transactions."""

    def __init__(
        self,
        generation_service: GenerationApplicationServiceProtocol,
        runtime_support: TaskExecutionRuntimeSupport,
        artifact_assembler: TaskExecutionArtifactAssembler,
        status_stage_service: TaskWorkerStatusStageService,
        execution_coordinator: TaskExecutionCoordinator,
        save_result: Callable[[dict[str, Any] | None], Awaitable[None]],
    ) -> None:
        self._generation_service = generation_service
        self._runtime_support = runtime_support
        self._artifact_assembler = artifact_assembler
        self._status_stage_service = status_stage_service
        self._execution_coordinator = execution_coordinator
        self._save_result = save_result

    async def generate_frame(
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
        pending_call = self._status_stage_service.create_pending_model_call(
            task,
            TaskStage.PLANNING,
            "generation.image",
            image_request,
            clip_index,
            f"{GenerationModelKinds.IMAGE}.{frame_role}",
        )
        await self._save_result(self._execution_coordinator.record_model_call(task, pending_call))
        try:
            image_run = await self._generation_service.create_run(image_request)
        except Exception as error:
            failed_call = self._status_stage_service.fail_model_call(pending_call, error)
            await self._save_result(self._execution_coordinator.record_model_call(task, failed_call))
            raise
        self._runtime_support.assert_task_still_active(task)
        image_result = self._result_map(image_run)
        image_metadata = map_value(image_result.get("metadata"))
        keyframe_source_url = first_non_blank(
            string_value(image_result.get("outputUrl")),
            string_value(image_metadata.get("remoteSourceUrl")),
        )
        completed_call = self._status_stage_service.complete_model_call(pending_call, image_run, image_result)
        await self._save_result(self._execution_coordinator.record_model_call(task, completed_call))
        self._status_stage_service.record_run_call_chain(task, TaskStage.PLANNING, image_run, image_result)
        image_material = self._artifact_assembler.create_image_material(
            task,
            image_run,
            image_result,
            clip_index,
            frame_role,
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
                material_url,
                keyframe_source_url,
                string_value(image_material.get("remoteUrl")),
            ),
            run_id_value=string_value(image_run.get("id")),
            material_value=image_material,
        )

    async def reuse_frame(
        self,
        task: TaskRecord,
        clip_index: int,
        source_url: str,
        frame_role: str,
        source_type: str,
    ) -> FrameResolution:
        image_material = self._artifact_assembler.create_reference_frame_material(
            task,
            clip_index,
            source_url,
            frame_role,
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

    @staticmethod
    def _result_map(run: dict[str, Any]) -> dict[str, Any]:
        result = run.get("result")
        return result if isinstance(result, dict) else {}
