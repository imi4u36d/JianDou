"""Refresh asynchronous workflow video generation results."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
from backend.domain.json_payloads import read_json_object, write_json_object
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import now_iso, safe_int, trim


class WorkflowVideoRefreshService:
    """Synchronize pending video versions with generation-run state."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        generation_service: Callable[[], Any],
        result_parser: WorkflowGenerationResultParser,
        row_factory: WorkflowPersistenceRowFactory,
        thumbnail_resolver: Callable[[str, str], str],
    ) -> None:
        self._db = db
        self._generation_service = generation_service
        self._result_parser = result_parser
        self._row_factory = row_factory
        self._thumbnail_resolver = thumbnail_resolver

    async def refresh(
        self,
        workflow: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> bool:
        changed = False
        timestamp = now_iso()
        for version in versions:
            if not self._should_refresh(version):
                continue
            output_summary = read_json_object(version.output_summary_json)
            run_id = self._run_id(version, output_summary)
            if not run_id:
                continue
            run = await self._load_run(run_id)
            if run is None:
                continue
            try:
                result = self._result_parser.parse_video_refresh_result(
                    run,
                    output_summary=output_summary,
                    current_status=trim(version.status).upper(),
                )
            except ValueError:
                continue

            if result.output_url:
                self._complete_version(workflow, version, versions, output_summary, run_id, result, timestamp)
                changed = True
                continue
            if result.run_status in {"failed", "error"}:
                output_summary["taskStatus"] = result.task_status or "FAILED"
                output_summary["error"] = result.error
                version.status = "FAILED"
                version.output_summary_json = write_json_object(output_summary)
                version.update_time = timestamp
                changed = True
            elif result.task_status:
                output_summary["taskStatus"] = result.task_status
                version.output_summary_json = write_json_object(output_summary)
                version.update_time = timestamp
                changed = True

        if changed:
            await self._db.commit()
        return changed

    @staticmethod
    def _should_refresh(version: BizStageVersion) -> bool:
        if version.stage_type != WorkflowStage.VIDEO.value or version.is_deleted != 0:
            return False
        return trim(version.status).upper() != "COMPLETED" or not trim(version.download_url)

    @staticmethod
    def _run_id(version: BizStageVersion, output_summary: dict[str, Any]) -> str:
        return trim(output_summary.get("runId")) or trim(
            read_json_object(version.model_call_summary_json).get("runId")
        )

    async def _load_run(self, run_id: str) -> dict[str, Any] | None:
        try:
            run = await self._generation_service().get_run(run_id)
        except Exception:  # noqa: S110 — refresh is intentionally best-effort
            return None
        return run if isinstance(run, dict) else None

    def _complete_version(
        self,
        workflow: BizStageWorkflow,
        version: BizStageVersion,
        versions: list[BizStageVersion],
        output_summary: dict[str, Any],
        run_id: str,
        result: Any,
        timestamp: str,
    ) -> None:
        asset_id = trim(version.material_asset_id)
        if not asset_id:
            asset = self._row_factory.create_material_asset(
                wf=workflow,
                stage_type=WorkflowStage.VIDEO.value,
                clip_index=safe_int(version.clip_index, 0),
                version_no=safe_int(version.version_no, 1),
                media_type="video",
                title=version.title or f"镜头 {version.clip_index} 视频",
                public_url=result.output_url,
                mime_type=result.mime_type,
                width=result.width,
                height=result.height,
                duration_seconds=result.duration_seconds,
                origin_provider=result.origin_provider,
                origin_model=result.origin_model,
                remote_task_id=result.remote_task_id,
                remote_url=result.remote_source_url,
                thumbnail_url=self._thumbnail_resolver("video", result.output_url),
                metadata={
                    "runId": run_id,
                    "taskId": result.remote_task_id,
                    "taskStatus": result.task_status,
                    "remoteSourceUrl": result.remote_source_url,
                },
            )
            self._db.add(asset)
            asset_id = asset.material_asset_id

        output_summary.update(
            {
                "fileUrl": result.output_url,
                "previewUrl": result.output_url,
                "taskStatus": result.task_status or "COMPLETED",
                "remoteSourceUrl": result.remote_source_url,
            }
        )
        version.status = "COMPLETED"
        version.material_asset_id = asset_id
        version.preview_url = result.output_url
        version.download_url = result.output_url
        version.output_summary_json = write_json_object(output_summary)
        self._select_version(versions, version, timestamp)
        workflow.current_stage = WorkflowStage.JOINED.value
        workflow.status = WorkflowStatus.READY.value
        workflow.update_time = timestamp

    @staticmethod
    def _select_version(
        versions: list[BizStageVersion],
        selected_version: BizStageVersion,
        timestamp: str,
    ) -> None:
        for candidate in versions:
            if (
                candidate.stage_type == WorkflowStage.VIDEO.value
                and candidate.clip_index == selected_version.clip_index
                and candidate.is_deleted == 0
            ):
                candidate.selected = 1 if candidate.stage_version_id == selected_version.stage_version_id else 0
                candidate.update_time = timestamp
