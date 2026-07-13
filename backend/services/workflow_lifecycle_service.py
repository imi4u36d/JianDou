"""Workflow creation, settings, reuse, deletion, and lifecycle field mutations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import AutoPilotState, WorkflowStage, WorkflowStatus
from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL
from backend.domain.json_payloads import write_json_object
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.shared import now_iso, random_id, safe_int, trim

DEFAULT_MIN_DURATION_SECONDS = 5
DEFAULT_MAX_DURATION_SECONDS = 12

ModelValidator = Callable[[int, str, str, str], Awaitable[None]]


def default_video_size(aspect_ratio: str | None) -> str:
    return "1280*720" if trim(aspect_ratio) == "16:9" else "720*1280"


def aspect_ratio_from_asset(asset: BizMaterialAsset) -> str:
    width = safe_int(asset.width, 0)
    height = safe_int(asset.height, 0)
    if width > 0 and height > 0:
        ratio = width / height
        if 0.95 <= ratio <= 1.05:
            return "1:1"
        if ratio > 1:
            return "16:9"
    return "9:16"


def normalize_duration_mode(
    duration_mode: str | None,
    min_seconds: int | None,
    max_seconds: int | None,
) -> str:
    mode = trim(duration_mode).lower()
    if mode in ("manual", "auto"):
        return mode
    return "manual" if (min_seconds is not None or max_seconds is not None) else "auto"


def duration_bounds(request: dict[str, Any], duration_mode: str) -> tuple[int, int]:
    if duration_mode == "auto":
        return DEFAULT_MIN_DURATION_SECONDS, DEFAULT_MAX_DURATION_SECONDS
    minimum = max(1, safe_int(request.get("minDurationSeconds"), 1))
    maximum = max(safe_int(request.get("maxDurationSeconds", minimum)), minimum)
    return minimum, maximum


class WorkflowLifecycleService:
    """Persist workflow lifecycle changes without mapping API response views."""

    def __init__(self, db: AsyncSession, *, model_validator: ModelValidator) -> None:
        self._db = db
        self._model_validator = model_validator

    async def create(
        self,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow:
        workflow_id = f"wf_{random_id()[:12]}"
        aspect_ratio = trim(request.get("aspectRatio", "9:16"))
        duration_mode = normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_duration, max_duration = duration_bounds(request, duration_mode)
        text_model = trim(request.get("textAnalysisModel"), "")
        image_model = trim(request.get("imageModel"), DEFAULT_OPENAI_IMAGE_MODEL)
        video_model = trim(request.get("videoModel"), "")
        execution_mode = trim(request.get("executionMode"), "manual")
        if execution_mode not in ("auto", "manual"):
            execution_mode = "manual"
        await self._model_validator(owner_user_id or 0, text_model, image_model, video_model)

        timestamp = now_iso()
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id or 0,
            title=trim(request.get("title"), "未命名工作流"),
            transcript_text=trim(request.get("transcriptText"), ""),
            aspect_ratio=aspect_ratio,
            text_analysis_model=text_model,
            image_model=image_model,
            video_model=video_model,
            video_size=trim(request.get("videoSize"), default_video_size(aspect_ratio)),
            keyframe_seed=request.get("keyframeSeed") or request.get("seed"),
            video_seed=request.get("videoSeed") or request.get("seed"),
            duration_mode=duration_mode,
            execution_mode=execution_mode,
            auto_pilot_state=AutoPilotState.IDLE.value,
            auto_pilot_next_stage="",
            auto_pilot_error_message="",
            auto_pilot_started_at="",
            auto_pilot_paused_at="",
            task_seed=request.get("seed"),
            min_duration_seconds=min_duration,
            max_duration_seconds=max_duration,
            status=WorkflowStatus.DRAFT.value,
            current_stage=WorkflowStage.STORYBOARD.value,
            selected_storyboard_version_id="",
            final_join_asset_id="",
            effect_rating=None,
            effect_rating_note="",
            metadata_json="{}",
            timezone_offset_minutes=0,
            remark="",
            create_time=timestamp,
            update_time=timestamp,
            is_deleted=0,
        )
        self._db.add(workflow)
        if execution_mode == "auto" and owner_user_id:
            await self._charge_auto_workflow(workflow, owner_user_id)
        await self._db.commit()
        return workflow

    async def create_from_material(
        self,
        *,
        asset_id: str,
        owner_user_id: int,
        mode: str = "clone",
    ) -> BizStageWorkflow | None:
        asset = await self._require_material_asset(asset_id, owner_user_id)
        if asset is None:
            return None
        workflow_id = f"wf_{random_id()[:12]}"
        timestamp = now_iso()
        aspect_ratio = aspect_ratio_from_asset(asset)
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id,
            title=f"{trim(asset.title, '素材')}复用",
            transcript_text="",
            aspect_ratio=aspect_ratio,
            text_analysis_model="",
            image_model="",
            video_model="",
            video_size=default_video_size(aspect_ratio),
            keyframe_seed=None,
            video_seed=None,
            duration_mode="auto",
            execution_mode="manual",
            auto_pilot_state=AutoPilotState.IDLE.value,
            auto_pilot_next_stage="",
            auto_pilot_error_message="",
            auto_pilot_started_at="",
            auto_pilot_paused_at="",
            task_seed=None,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            max_duration_seconds=DEFAULT_MAX_DURATION_SECONDS,
            status=WorkflowStatus.DRAFT.value,
            current_stage=WorkflowStage.STORYBOARD.value,
            selected_storyboard_version_id="",
            final_join_asset_id=asset.material_asset_id,
            effect_rating=None,
            effect_rating_note="",
            metadata_json=write_json_object(
                {
                    "source": "material_reuse",
                    "sourceMaterialAssetId": asset.material_asset_id,
                    "reuseMode": trim(mode, "clone"),
                }
            ),
            timezone_offset_minutes=0,
            remark="",
            create_time=timestamp,
            update_time=timestamp,
            is_deleted=0,
        )
        asset.workflow_id = asset.workflow_id or workflow_id
        asset.update_time = timestamp
        self._db.add(workflow)
        await self._db.commit()
        return workflow

    async def delete(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        asset_ids = {version.material_asset_id for version in versions if version.material_asset_id}
        if workflow.final_join_asset_id:
            asset_ids.add(workflow.final_join_asset_id)
        timestamp = now_iso()
        for version in versions:
            version.selected = 0
            version.is_deleted = 1
            version.update_time = timestamp
        for asset_id in asset_ids:
            await self._mark_asset_deleted(asset_id, timestamp)
        workflow.is_deleted = 1
        workflow.update_time = timestamp
        await self._db.commit()
        return workflow

    async def update_settings(
        self,
        workflow_id: str,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        aspect_ratio = trim(request.get("aspectRatio", "9:16"))
        duration_mode = normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_duration, max_duration = duration_bounds(request, duration_mode)
        text_model = trim(request.get("textAnalysisModel"), "")
        image_model = trim(request.get("imageModel"), DEFAULT_OPENAI_IMAGE_MODEL)
        video_model = trim(request.get("videoModel"), "")
        await self._model_validator(workflow.owner_user_id, text_model, image_model, video_model)

        workflow.aspect_ratio = aspect_ratio
        workflow.text_analysis_model = text_model
        workflow.image_model = image_model
        workflow.video_model = video_model
        workflow.video_size = trim(request.get("videoSize"), default_video_size(aspect_ratio))
        workflow.keyframe_seed = request.get("keyframeSeed")
        workflow.video_seed = request.get("videoSeed")
        workflow.duration_mode = duration_mode
        workflow.min_duration_seconds = min_duration
        workflow.max_duration_seconds = max_duration
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def update_auto_pilot_fields(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        *,
        execution_mode: str | None = None,
        auto_pilot_state: str | None = None,
        auto_pilot_next_stage: str | None = None,
        auto_pilot_error_message: str | None = None,
        auto_pilot_started_at: str | None = None,
        auto_pilot_paused_at: str | None = None,
    ) -> BizStageWorkflow | None:
        workflow = await self._require_workflow(workflow_id, owner_user_id)
        if workflow is None:
            return None
        if execution_mode is not None:
            workflow.execution_mode = execution_mode
        if auto_pilot_state is not None:
            workflow.auto_pilot_state = auto_pilot_state
            workflow.auto_pilot_current_task = ""
            if auto_pilot_state == AutoPilotState.QUEUED.value:
                workflow.status = WorkflowStatus.READY.value
                workflow.auto_pilot_error_message = ""
        if auto_pilot_next_stage is not None:
            workflow.auto_pilot_next_stage = auto_pilot_next_stage
        if auto_pilot_error_message is not None:
            workflow.auto_pilot_error_message = auto_pilot_error_message
        if auto_pilot_started_at is not None:
            workflow.auto_pilot_started_at = auto_pilot_started_at
        if auto_pilot_paused_at is not None:
            workflow.auto_pilot_paused_at = auto_pilot_paused_at
        workflow.update_time = now_iso()
        await self._db.commit()
        return workflow

    async def _charge_auto_workflow(self, workflow: BizStageWorkflow, owner_user_id: int) -> None:
        from backend.services.credit_service import CreditService

        try:
            credit_charge = await CreditService(self._db).charge(
                owner_user_id,
                "VIDEO_GENERATION",
                workflow_id=workflow.workflow_id,
                reason="自动工作流创建扣费",
                commit=False,
            )
        except Exception:
            await self._db.rollback()
            raise
        workflow.metadata_json = write_json_object({"creditCharge": credit_charge})

    async def _require_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> BizStageWorkflow | None:
        filters = [
            BizStageWorkflow.workflow_id == workflow_id,
            BizStageWorkflow.is_deleted == 0,
        ]
        if owner_user_id is not None:
            filters.append(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self._db.execute(select(BizStageWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def _require_material_asset(
        self,
        asset_id: str,
        owner_user_id: int,
    ) -> BizMaterialAsset | None:
        result = await self._db.execute(
            select(BizMaterialAsset).where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.owner_user_id == owner_user_id,
                BizMaterialAsset.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def _list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        result = await self._db.execute(
            select(BizStageVersion)
            .where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.is_deleted == 0,
            )
            .order_by(
                BizStageVersion.stage_type,
                BizStageVersion.clip_index,
                BizStageVersion.version_no.desc(),
            )
        )
        return list(result.scalars().all())

    async def _mark_asset_deleted(self, asset_id: str, timestamp: str) -> None:
        await self._db.execute(
            update(BizMaterialAsset)
            .where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.is_deleted == 0,
            )
            .values(selected_for_next=0, is_deleted=1, update_time=timestamp)
        )
