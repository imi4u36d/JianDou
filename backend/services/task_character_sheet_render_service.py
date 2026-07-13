"""Character-sheet generation within the task render stage."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_worker_status_stage_service import TaskStage, TaskWorkerExecutionContext
from backend.shared import first_non_blank, map_value, string_value


class TaskCharacterSheetRenderService:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

    async def ensure_character_sheets(
        self,
        task: TaskRecord,
        run_context: TaskWorkerExecutionContext,
        character_definitions: list[Any],
        width: int,
        height: int,
        image_run_ids: list[str],
    ) -> list[str]:
        owner = self._owner
        if not character_definitions:
            owner._put_execution_context(task, "characterSheetUrls", [])
            return []

        existing = owner._existing_character_sheet_urls(task)
        resolved_urls: list[str] = []
        generated_count = 0
        reused_count = 0
        await owner._save_result(owner._execution_coordinator.record_trace(
            task,
            TaskStage.PLANNING,
            "planning.character_sheets_started",
            "任务开始生成角色三视图设定图。",
            "INFO",
            {"characterCount": len(character_definitions)},
        ))

        for index, character in enumerate(character_definitions, start=1):
            existing_url = existing.get(index, "")
            if existing_url:
                resolved_urls.append(existing_url)
                reused_count += 1
                continue

            sheet_request = owner._runtime_support.build_character_sheet_run_request(
                task, index, character, width, height
            )
            pending_model_call = owner._status_stage_service.create_pending_model_call(
                task,
                TaskStage.PLANNING,
                "generation.image",
                sheet_request,
                1000 + index,
                "image.character_sheet",
            )
            await owner._save_result(owner._execution_coordinator.record_model_call(task, pending_model_call))
            try:
                sheet_run = await owner._generation_application_service.create_run(sheet_request)
            except Exception as error:
                await owner._save_result(owner._execution_coordinator.record_model_call(
                    task,
                    owner._status_stage_service.fail_model_call(pending_model_call, error),
                ))
                raise

            owner._runtime_support.assert_task_still_active(task)
            sheet_result = owner._result_map(sheet_run)
            sheet_metadata = map_value(sheet_result.get("metadata"))
            sheet_url = first_non_blank(
                string_value(sheet_metadata.get("remoteSourceUrl")),
                string_value(sheet_result.get("outputUrl")),
            )
            if not sheet_url:
                raise ValueError(f"角色 {index} 三视图生成结果为空，未返回可用输出地址。")

            sheet_model_call = owner._status_stage_service.complete_model_call(
                pending_model_call, sheet_run, sheet_result
            )
            await owner._save_result(owner._execution_coordinator.record_model_call(task, sheet_model_call))
            owner._status_stage_service.record_run_call_chain(task, TaskStage.PLANNING, sheet_run, sheet_result)
            sheet_material = owner._artifact_assembler.create_character_sheet_material(
                task, sheet_run, sheet_result, index, character
            )
            await owner._save_result(owner._execution_coordinator.record_material(task, sheet_material))
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

            await owner._save_result(owner._status_stage_service.record_stage_run(
                task,
                run_context,
                50 + index,
                TaskStage.PLANNING,
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
            ))

        owner._put_execution_context(task, "characterSheetUrls", resolved_urls)
        owner._put_execution_context(task, "characterSheetCount", len(resolved_urls))
        if owner._task_repository:
            await owner._task_repository.save(task)
        await owner._save_result(owner._execution_coordinator.record_trace(
            task,
            TaskStage.PLANNING,
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
        ))
        return resolved_urls
