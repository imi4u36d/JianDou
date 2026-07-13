"""Workspace image-generation pipeline extracted from the worker orchestrator."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_worker_status_stage_service import (
    TaskStage as _TaskStage,
)
from backend.services.task_worker_status_stage_service import (
    TaskWorkerExecutionContext,
)
from backend.shared import first_non_blank, map_value, safe_int, string_value


class TaskWorkspaceImageService:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

    async def process(
        self, task: TaskRecord, run_context: TaskWorkerExecutionContext, dimensions: list[int]
    ) -> None:
        output_count = self._owner._runtime_support.resolve_workspace_image_output_count(task)
        if dimensions[0] > 0 and dimensions[1] > 0:
            self._owner._put_execution_context(task, "imageSize", f"{dimensions[0]}x{dimensions[1]}")
        else:
            self._owner._put_execution_context(task, "imageSize", None)
        self._owner._put_execution_context(task, "requestedImageOutputCount", output_count)
        self._owner._put_execution_context(task, "workerInstanceId", run_context.worker_instance_id)
        await self._owner._save_result(
            self._owner._execution_coordinator.mark_active_attempt_running(task, run_context.worker_instance_id)
        )
        await self._owner._save_result(
            self._owner._status_stage_service.update_status(
                task,
                run_context,
                "RENDERING",
                5,
                _TaskStage.RENDER,
                "task.claimed",
                "任务已被 worker 领取。",
            )
        )
        self._owner._runtime_support.assert_task_still_active(task)

        await self._owner._save_result(
            self._owner._status_stage_service.update_status(
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
                await self._owner._save_result(
                    self._owner._status_stage_service.update_status(
                        task,
                        run_context,
                        "RENDERING",
                        progress,
                        _TaskStage.RENDER,
                        "task.rendering",
                        f"工作台图片任务正在生成第 {output_index}/{output_count} 张。",
                    )
                )

            image_request = self._owner._runtime_support.build_workspace_image_run_request(
                task,
                dimensions[0],
                dimensions[1],
                output_index=output_index,
            )
            pending_model_call = self._owner._status_stage_service.create_pending_model_call(
                task,
                _TaskStage.RENDER,
                "generation.image",
                image_request,
                output_index,
                "workspace_image",
            )
            await self._owner._save_result(self._owner._execution_coordinator.record_model_call(task, pending_model_call))
            try:
                image_run = await self._owner._generation_application_service.create_run(image_request)
            except Exception as ex:
                await self._owner._save_result(
                    self._owner._execution_coordinator.record_model_call(
                        task, self._owner._status_stage_service.fail_model_call(pending_model_call, ex)
                    )
                )
                raise
            self._owner._runtime_support.assert_task_still_active(task)
            image_result = self._owner._result_map(image_run)
            image_metadata = map_value(image_result.get("metadata"))
            actual_width = safe_int(image_result.get("width"), 0) or safe_int(image_metadata.get("artifactWidth"), 0)
            actual_height = safe_int(image_result.get("height"), 0) or safe_int(image_metadata.get("artifactHeight"), 0)
            if actual_width > 0 and actual_height > 0:
                actual_image_size = f"{actual_width}x{actual_height}"
                self._owner._put_execution_context(task, "imageSize", actual_image_size)
                self._owner._put_execution_context(task, "actualImageSize", actual_image_size)
            output_url = first_non_blank(
                string_value(image_result.get("outputUrl")),
                string_value(image_metadata.get("outputUrl")),
                string_value(image_metadata.get("fileUrl")),
            )
            if not output_url:
                raise ValueError("图片生成结果为空，未返回可用输出地址。")

            image_model_call = self._owner._status_stage_service.complete_model_call(
                pending_model_call, image_run, image_result
            )
            await self._owner._save_result(self._owner._execution_coordinator.record_model_call(task, image_model_call))
            self._owner._status_stage_service.record_run_call_chain(task, _TaskStage.RENDER, image_run, image_result)
            image_material = self._owner._artifact_assembler.create_workspace_image_material(
                task,
                image_run,
                image_result,
                output_index=output_index,
            )
            await self._owner._save_result(self._owner._execution_coordinator.record_material(task, image_material))
            stored_output_url = first_non_blank(string_value(image_material.get("fileUrl")), output_url)
            image_output = self._owner._artifact_assembler.create_image_result(
                task,
                image_run,
                image_result,
                image_material,
                image_model_call,
                output_index=output_index,
            )
            await self._owner._save_result(self._owner._execution_coordinator.record_result(task, image_output))
            image_run_id = string_value(image_run.get("id"))
            if image_run_id:
                image_run_ids.append(image_run_id)
            output_urls.append(stored_output_url)
            material_asset_ids.append(string_value(image_material.get("id")))
            latest_image_run = image_run
            latest_output_url = stored_output_url

        self._owner._put_execution_context(task, "latestImageRunId", string_value(latest_image_run.get("id")))
        self._owner._put_execution_context(task, "latestImageRunIds", image_run_ids)
        self._owner._put_execution_context(task, "latestImageOutputUrl", latest_output_url)
        self._owner._put_execution_context(task, "latestImageOutputUrls", output_urls)
        self._owner._put_execution_context(task, "latestMaterialAssetId", material_asset_ids[-1] if material_asset_ids else "")
        self._owner._put_execution_context(task, "latestMaterialAssetIds", material_asset_ids)
        await self._owner._task_repository.save(task)
        await self._owner._save_result(
            self._owner._status_stage_service.record_stage_run(
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
        await self._owner._save_result(
            self._owner._status_stage_service.complete_workspace_image_task(
                task,
                run_context,
                latest_image_run,
                latest_output_url,
                output_count=output_count,
                image_run_ids=image_run_ids,
            )
        )
