"""Generate and persist workflow storyboard versions."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.shared import random_id, safe_int, trim

logger = logging.getLogger(__name__)

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value


def storyboard_generation_error(error: Exception) -> ValueError:
    raw_error = str(error)
    normalized = raw_error.lower()
    if "missing api key" in normalized or "missing api key or base url" in normalized:
        return ValueError("当前用户未设置对应模型 Key，请先在用户管理中配置 Key。")
    return ValueError(f"分镜生成失败：{raw_error}")


class WorkflowStoryboardGenerationService:
    """Own storyboard validation, model invocation, and version persistence."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        generation_service: Callable[[], Any],
        request_builder: WorkflowGenerationRequestBuilder,
        result_parser: WorkflowGenerationResultParser,
        row_factory: WorkflowPersistenceRowFactory,
    ) -> None:
        self._db = db
        self._generation_service = generation_service
        self._request_builder = request_builder
        self._result_parser = result_parser
        self._row_factory = row_factory

    async def generate(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        if not trim(workflow.transcript_text):
            raise ValueError("请先填写正文内容，再生成分镜。")
        if not trim(workflow.text_analysis_model):
            raise ValueError("请先选择文本模型。")

        version_no = await self._next_version_no(workflow_id)
        request = self._request_builder.build_storyboard_request(workflow)
        try:
            generation_result = await self._generation_service().create_run(request)
        except Exception as error:
            logger.warning("Storyboard generation failed: %s", error)
            raise storyboard_generation_error(error) from error

        script = self._result_parser.parse_script_result(generation_result)
        version = self._row_factory.create_stage_version(
            wf=workflow,
            stage_version_id=f"sv_{random_id()[:12]}",
            stage_type=STAGE_STORYBOARD,
            clip_index=0,
            version_no=version_no,
            title=f"分镜版本 {version_no}",
            status="COMPLETED",
            selected=0,
            input_summary={"transcriptLength": len(workflow.transcript_text or "")},
            output_summary=script.output_summary,
            model_call_summary=script.model_call_summary,
        )
        self._db.add(version)
        await self._db.commit()
        return workflow

    async def _require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None,
    ) -> BizStageWorkflow | None:
        filters = [BizStageWorkflow.workflow_id == workflow_id, BizStageWorkflow.is_deleted == 0]
        if owner_user_id is not None:
            filters.append(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizStageWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def _next_version_no(self, workflow_id: str) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_STORYBOARD,
                BizStageVersion.is_deleted == 0,
            )
        )
        return safe_int(result.scalar(), 0) + 1
