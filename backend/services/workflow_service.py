"""Workflow service — Python translation of WorkflowApplicationService (Java).

Handles the multi-stage creative workflow lifecycle:
  STORYBOARD -> KEYFRAME -> VIDEO -> JOINED
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import AutoPilotState, WorkflowStage, WorkflowStatus
from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL
from backend.domain.json_payloads import read_json_object, write_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.services.workflow_view_mapper import WorkflowViewMapper
from backend.shared import first_non_blank, now_iso, random_id, safe_float, safe_int, trim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (mirroring WorkflowConstants.java)
# ---------------------------------------------------------------------------
STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
STAGE_JOINED = WorkflowStage.JOINED.value

STATUS_DRAFT = WorkflowStatus.DRAFT.value
STATUS_READY = WorkflowStatus.READY.value
STATUS_RUNNING = WorkflowStatus.RUNNING.value
STATUS_PAUSED = WorkflowStatus.PAUSED.value
STATUS_COMPLETED = WorkflowStatus.COMPLETED.value
STATUS_FAILED = WorkflowStatus.FAILED.value

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"
DEFAULT_MIN_DURATION_SECONDS = 5
DEFAULT_MAX_DURATION_SECONDS = 12

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------








def _default_video_size(aspect_ratio: str | None) -> str:
    return "1280*720" if trim(aspect_ratio) == "16:9" else "720*1280"


def _aspect_ratio_from_asset(asset: BizMaterialAsset) -> str:
    width = safe_int(asset.width, 0)
    height = safe_int(asset.height, 0)
    if width > 0 and height > 0:
        ratio = width / height
        if 0.95 <= ratio <= 1.05:
            return "1:1"
        if ratio > 1:
            return "16:9"
    return "9:16"


def _normalize_duration_mode(
    duration_mode: str | None,
    min_seconds: int | None,
    max_seconds: int | None,
) -> str:
    mode = trim(duration_mode).lower()
    if mode in ("manual", "auto"):
        return mode
    return "manual" if (min_seconds is not None or max_seconds is not None) else "auto"


def _dimensions_from_aspect_ratio(aspect_ratio: str | None) -> tuple[int, int]:
    ar = trim(aspect_ratio)
    if ar == "16:9":
        return 1824, 1024
    if ar == "1:1":
        return 1024, 1024
    return 1024, 1824


def _dimensions_from_size(value: str | None, fallback_aspect_ratio: str | None = None) -> tuple[int, int]:
    raw = trim(value).lower().replace("x", "*")
    match = re.search(r"(\d{3,5})\s*\*\s*(\d{3,5})", raw)
    if match:
        return safe_int(match.group(1), 0), safe_int(match.group(2), 0)
    if "1280" in raw and "720" in raw:
        return 1280, 720
    if "720" in raw and "1280" in raw:
        return 720, 1280
    return _dimensions_from_aspect_ratio(fallback_aspect_ratio)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


# =============================================================================
# WORKFLOW SERVICE
# =============================================================================

def _read_json(text: str | None) -> dict[str, Any]:
    return read_json_object(text)


def _write_json(data: dict[str, Any]) -> str:
    return write_json_object(data)


class WorkflowService:
    """Multi-stage creative workflow service."""

    def __init__(
        self,
        db: AsyncSession,
        generation_service: Any | None = None,
        media_service: Any | None = None,
    ) -> None:
        self.db = db
        self._generation_service = generation_service
        self._media_service = media_service
        self._view_mapper = WorkflowViewMapper(self._storyboard_plan)
        self._generation_request_builder = WorkflowGenerationRequestBuilder()
        self._generation_result_parser = WorkflowGenerationResultParser()
        self._row_factory = WorkflowPersistenceRowFactory()

    def _get_generation_service(self):
        if self._generation_service is None:
            raise RuntimeError("generation service not configured")
        return self._generation_service

    def _material_thumbnail_url(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str] | None = None,
    ) -> str:
        if self._media_service is None or not public_url:
            return ""
        try:
            return trim(
                self._media_service.ensure_media_thumbnail(
                    media_type,
                    public_url,
                    candidate_image_urls or [],
                    480,
                )
            )
        except Exception as ex:
            logger.warning("Failed to generate %s thumbnail for workflow material: %s", media_type, ex)
            return ""

    async def _validate_generation_models(
        self,
        owner_user_id: int,
        text_model: str,
        image_model: str,
        video_model: str,
    ) -> None:
        gen_service = self._get_generation_service()
        factory = getattr(gen_service, "_factory", None)
        resolver = getattr(factory, "_config_resolver", None)
        if resolver is None:
            raise ValueError("模型配置服务未初始化，请重启服务后重试。")

        checks = [
            ("文本模型", text_model, "text"),
            ("关键帧模型", image_model, "image"),
            ("视频模型", video_model, "video"),
        ]
        for label, model, kind in checks:
            value = trim(model)
            if not value:
                raise ValueError(f"请先选择{label}。")
            try:
                if kind == "text":
                    profile = resolver.resolve_text_profile(value, owner_user_id)
                    provider = getattr(profile, "provider", "")
                    api_key = getattr(profile, "api_key", "")
                    base_url = getattr(profile, "base_url", "")
                    task_base_url = True
                else:
                    profile = resolver.resolve_media_profile(value, kind, owner_user_id)
                    provider = getattr(profile, "provider", "")
                    api_key = getattr(profile, "api_key", "")
                    base_url = getattr(profile, "base_url", "")
                    task_base_url = kind != "video" or bool(getattr(profile, "task_base_url", ""))
                ready = getattr(profile, "ready", False)
            except Exception as exc:
                raise ValueError(f"{label}不可用：{value}") from exc
            if not provider:
                raise ValueError(f"{label}不可用：{value}")
            if not api_key:
                raise ValueError(f"当前用户未设置{label} Key，请先在用户管理中配置 Key。")
            if not base_url:
                raise ValueError(f"{label}缺少 base_url，请检查模型配置。")
            if not task_base_url:
                raise ValueError(f"{label}缺少 task_base_url，请检查模型配置。")
            if not ready:
                raise ValueError(f"{label}配置未就绪，请检查用户 Key 和模型配置。")

    # ------------------------------------------------------------------
    # Workflow CRUD
    # ------------------------------------------------------------------

    async def create_workflow(
        self,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Create a draft workflow."""
        workflow_id = f"wf_{random_id()[:12]}"
        aspect_ratio = trim(request.get("aspectRatio", "9:16"))
        keyframe_seed = request.get("keyframeSeed") or request.get("seed")
        video_seed = request.get("videoSeed") or request.get("seed")
        duration_mode = _normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_dur = (
            DEFAULT_MIN_DURATION_SECONDS
            if duration_mode == "auto"
            else max(1, safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(safe_int(request.get("maxDurationSeconds", min_dur)), min_dur)
        )
        text_model = trim(request.get("textAnalysisModel"), "")
        image_model = trim(request.get("imageModel"), DEFAULT_OPENAI_IMAGE_MODEL)
        video_model = trim(request.get("videoModel"), "")
        execution_mode = trim(request.get("executionMode"), "manual")
        if execution_mode not in ("auto", "manual"):
            execution_mode = "manual"
        await self._validate_generation_models(owner_user_id or 0, text_model, image_model, video_model)
        now = now_iso()
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id or 0,
            title=trim(request.get("title"), "未命名工作流"),
            transcript_text=trim(request.get("transcriptText"), ""),
            aspect_ratio=aspect_ratio,
            text_analysis_model=text_model,
            image_model=image_model,
            video_model=video_model,
            video_size=trim(request.get("videoSize"), _default_video_size(aspect_ratio)),
            keyframe_seed=keyframe_seed,
            video_seed=video_seed,
            duration_mode=duration_mode,
            execution_mode=execution_mode,
            auto_pilot_state="idle",
            auto_pilot_next_stage="",
            auto_pilot_error_message="",
            auto_pilot_started_at="",
            auto_pilot_paused_at="",
            task_seed=request.get("seed"),
            min_duration_seconds=min_dur,
            max_duration_seconds=max_dur,
            status=STATUS_DRAFT,
            current_stage=STAGE_STORYBOARD,
            selected_storyboard_version_id="",
            final_join_asset_id="",
            effect_rating=None,
            effect_rating_note="",
            metadata_json="{}",
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )
        self.db.add(workflow)
        if execution_mode == "auto" and owner_user_id:
            from backend.services.credit_service import CreditService

            try:
                credit_charge = await CreditService(self.db).charge(
                    owner_user_id,
                    "VIDEO_GENERATION",
                    workflow_id=workflow_id,
                    reason="自动工作流创建扣费",
                    commit=False,
                )
            except Exception:
                await self.db.rollback()
                raise
            workflow.metadata_json = write_json_object({"creditCharge": credit_charge})
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def create_workflow_from_material(
        self,
        *,
        asset_id: str,
        owner_user_id: int,
        mode: str = "clone",
    ) -> dict[str, Any] | None:
        """Create a persisted draft workflow that reuses an existing material asset."""
        asset = await self._require_material_asset(asset_id, owner_user_id)
        if asset is None:
            return None
        workflow_id = f"wf_{random_id()[:12]}"
        title = f"{trim(asset.title, '素材')}复用"
        now = now_iso()
        aspect_ratio = _aspect_ratio_from_asset(asset)
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id,
            title=title,
            transcript_text="",
            aspect_ratio=aspect_ratio,
            text_analysis_model="",
            image_model="",
            video_model="",
            video_size=_default_video_size(aspect_ratio),
            keyframe_seed=None,
            video_seed=None,
            duration_mode="auto",
            execution_mode="manual",
            auto_pilot_state=AutoPilotState.IDLE,
            auto_pilot_next_stage="",
            auto_pilot_error_message="",
            auto_pilot_started_at="",
            auto_pilot_paused_at="",
            task_seed=None,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            max_duration_seconds=DEFAULT_MAX_DURATION_SECONDS,
            status=STATUS_DRAFT,
            current_stage=STAGE_STORYBOARD,
            selected_storyboard_version_id="",
            final_join_asset_id=asset.material_asset_id,
            effect_rating=None,
            effect_rating_note="",
            metadata_json=_write_json({
                "source": "material_reuse",
                "sourceMaterialAssetId": asset.material_asset_id,
                "reuseMode": trim(mode, "clone"),
            }),
            timezone_offset_minutes=0,
            remark="",
            create_time=now,
            update_time=now,
            is_deleted=0,
        )
        asset.workflow_id = asset.workflow_id or workflow_id
        asset.update_time = now
        self.db.add(workflow)
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def list_workflows(
        self,
        owner_user_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """List user's workflows with version counts."""
        is_paginated = offset is not None or limit is not None
        page_offset = max(0, offset or 0)
        page_limit = max(1, limit or 10)
        stmt = (
            select(BizStageWorkflow)
            .where(BizStageWorkflow.is_deleted == 0)
        )
        count_stmt = select(func.count()).select_from(BizStageWorkflow).where(BizStageWorkflow.is_deleted == 0)
        if owner_user_id is not None:
            stmt = stmt.where(BizStageWorkflow.owner_user_id == owner_user_id)
            count_stmt = count_stmt.where(BizStageWorkflow.owner_user_id == owner_user_id)
        stmt = self._apply_workflow_list_filters(stmt, q, status)
        count_stmt = self._apply_workflow_list_filters(count_stmt, q, status)
        stmt = self._apply_workflow_list_sort(stmt, sort)
        if is_paginated:
            stmt = stmt.offset(page_offset).limit(page_limit)
        result = await self.db.execute(stmt)
        workflows = result.scalars().all()

        rows: list[dict[str, Any]] = []
        for wf in workflows:
            versions = await self._list_stage_versions(wf.workflow_id)
            rows.append(self._view_mapper.to_workflow_summary(wf, versions))
        if is_paginated:
            total_result = await self.db.execute(count_stmt)
            return {
                "items": rows,
                "total": int(total_result.scalar_one() or 0),
                "offset": page_offset,
                "limit": page_limit,
            }
        return rows

    def _apply_workflow_list_filters(self, stmt: Any, q: str | None, status: str | None):
        keyword = trim(q or "")
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    BizStageWorkflow.title.ilike(like),
                    BizStageWorkflow.status.ilike(like),
                    BizStageWorkflow.current_stage.ilike(like),
                    BizStageWorkflow.aspect_ratio.ilike(like),
                    BizStageWorkflow.execution_mode.ilike(like),
                    BizStageWorkflow.auto_pilot_state.ilike(like),
                )
            )
        normalized_status = trim(status or "").lower()
        if not normalized_status or normalized_status == "all":
            return stmt
        if normalized_status == "active":
            return stmt.where(
                or_(
                    BizStageWorkflow.auto_pilot_state.in_(("queued", "running", "paused")),
                    BizStageWorkflow.status.in_(("DRAFT", "READY", "RUNNING", "PAUSED")),
                )
            )
        if normalized_status == "ready":
            return stmt.where(
                BizStageWorkflow.current_stage.in_(("storyboard", "keyframe", "video")),
                BizStageWorkflow.status.in_(("DRAFT", "READY", "RUNNING", "PAUSED")),
            )
        if normalized_status == "done":
            return stmt.where(
                or_(
                    BizStageWorkflow.status == "COMPLETED",
                    BizStageWorkflow.current_stage == "joined",
                    BizStageWorkflow.auto_pilot_state == "completed",
                )
            )
        return stmt.where(BizStageWorkflow.status == normalized_status.upper())

    def _apply_workflow_list_sort(self, stmt: Any, sort: str | None):
        normalized_sort = trim(sort or "").lower() or "created_desc"
        if normalized_sort == "updated_desc":
            return stmt.order_by(BizStageWorkflow.update_time.desc(), BizStageWorkflow.id.desc())
        if normalized_sort == "status_desc":
            return stmt.order_by(BizStageWorkflow.status.asc(), BizStageWorkflow.update_time.desc(), BizStageWorkflow.id.desc())
        return stmt.order_by(BizStageWorkflow.create_time.desc(), BizStageWorkflow.id.desc())

    async def get_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get full workflow detail with all versions and assets."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        if await self._refresh_video_versions(wf, versions):
            versions = await self._list_stage_versions(workflow_id)
        asset_map = await self._load_asset_map(versions, wf.final_join_asset_id)
        return self._view_mapper.to_workflow_detail(wf, versions, asset_map)

    async def delete_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Soft delete workflow and all versions."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        asset_ids: set[str] = set()
        now = now_iso()
        for v in versions:
            if v.material_asset_id:
                asset_ids.add(v.material_asset_id)
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
        if wf.final_join_asset_id:
            asset_ids.add(wf.final_join_asset_id)
        for aid in asset_ids:
            await self._mark_asset_deleted(aid)
        wf.is_deleted = 1
        wf.update_time = now
        await self.db.commit()
        return {"workflowId": workflow_id, "deleted": True}

    async def update_workflow_settings(
        self,
        workflow_id: str,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Update workflow parameters."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        aspect_ratio = trim(request.get("aspectRatio", "9:16"))
        duration_mode = _normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_dur = (
            DEFAULT_MIN_DURATION_SECONDS
            if duration_mode == "auto"
            else max(1, safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(safe_int(request.get("maxDurationSeconds"), min_dur), min_dur)
        )
        text_model = trim(request.get("textAnalysisModel"), "")
        image_model = trim(request.get("imageModel"), DEFAULT_OPENAI_IMAGE_MODEL)
        video_model = trim(request.get("videoModel"), "")
        await self._validate_generation_models(wf.owner_user_id, text_model, image_model, video_model)
        wf.aspect_ratio = aspect_ratio
        wf.text_analysis_model = text_model
        wf.image_model = image_model
        wf.video_model = video_model
        wf.video_size = trim(request.get("videoSize"), _default_video_size(aspect_ratio))
        wf.keyframe_seed = request.get("keyframeSeed")
        wf.video_seed = request.get("videoSeed")
        wf.duration_mode = duration_mode
        wf.min_duration_seconds = min_dur
        wf.max_duration_seconds = max_dur
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Auto-pilot field updates
    # ------------------------------------------------------------------

    async def _update_auto_pilot_fields(
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
    ) -> dict[str, Any] | None:
        """Update auto-pilot related fields on a workflow."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        now = now_iso()
        if execution_mode is not None:
            wf.execution_mode = execution_mode
        if auto_pilot_state is not None:
            wf.auto_pilot_state = auto_pilot_state
            wf.auto_pilot_current_task = ""  # clear task annotation on state change
            # When re-queuing (start/resume), sync workflow-level status back
            # to READY so the workflow is not stuck in FAILED/COMPLETED while
            # the auto-pilot is queued.  Also clear stale error messages.
            if auto_pilot_state == "queued":
                wf.status = WorkflowStatus.READY.value
                wf.auto_pilot_error_message = ""
        if auto_pilot_next_stage is not None:
            wf.auto_pilot_next_stage = auto_pilot_next_stage
        if auto_pilot_error_message is not None:
            wf.auto_pilot_error_message = auto_pilot_error_message
        if auto_pilot_started_at is not None:
            wf.auto_pilot_started_at = auto_pilot_started_at
        if auto_pilot_paused_at is not None:
            wf.auto_pilot_paused_at = auto_pilot_paused_at
        wf.update_time = now
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Storyboard
    # ------------------------------------------------------------------

    async def generate_storyboard(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a storyboard version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None

        # Check if transcript text exists
        if not wf.transcript_text or not wf.transcript_text.strip():
            raise ValueError("请先填写正文内容，再生成分镜。")

        # Create a new storyboard version
        version_id = f"sv_{random_id()[:12]}"

        # Count existing storyboard versions for version number
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_STORYBOARD,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0

        # Call real AI generation for storyboard
        gen_service = self._get_generation_service()
        text_model = trim(getattr(wf, 'text_analysis_model', ''))
        if not text_model:
            raise ValueError("请先选择文本模型。")

        generation_request = self._generation_request_builder.build_storyboard_request(wf)

        try:
            gen_result = await gen_service.create_run(generation_request)
        except Exception as ex:
            logger.warning("Storyboard generation failed: %s", ex)
            raw_error = str(ex)
            if "missing api key" in raw_error.lower() or "missing api key or base url" in raw_error.lower():
                raise ValueError("当前用户未设置对应模型 Key，请先在用户管理中配置 Key。") from ex
            raise ValueError(f"分镜生成失败：{raw_error}") from ex

        script_result = self._generation_result_parser.parse_script_result(gen_result)

        storyboard_version = self._row_factory.create_stage_version(
            wf=wf,
            stage_version_id=version_id,
            stage_type=STAGE_STORYBOARD,
            clip_index=0,
            version_no=version_count + 1,
            title=f"分镜版本 {version_count + 1}",
            status="COMPLETED",
            selected=0,
            input_summary={"transcriptLength": len(wf.transcript_text or "")},
            output_summary=script_result.output_summary,
            model_call_summary=script_result.model_call_summary,
        )

        self.db.add(storyboard_version)
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Select a storyboard version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_STORYBOARD, 0, version_id)
        wf.selected_storyboard_version_id = version_id
        wf.current_stage = STAGE_KEYFRAME
        wf.status = STATUS_READY
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def adjust_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        prompt: str | None = None,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Adjust an existing storyboard version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None

        # Verify the storyboard version exists
        version = await self._require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None

        # Update the version with adjustment info
        now = now_iso()
        version.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Keyframe
    # ------------------------------------------------------------------

    async def _resolve_character_sheet_urls(
        self,
        workflow_id: str,
    ) -> list[str]:
        """Return remote URLs of all selected character sheet keyframes.

        These are used as reference images so the image model preserves
        character identity when generating clip keyframes.
        """
        result = await self.db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE,
                BizStageVersion.selected == 1,
                BizStageVersion.is_deleted == 0,
            )
        )
        versions = result.scalars().all()
        urls: list[str] = []
        for v in versions:
            output = read_json_object(v.output_summary_json)
            url = trim(output.get("remoteSourceUrl"))
            if not url:
                url = trim(output.get("sheetUrl"))
            if not url:
                url = trim(output.get("fileUrl"))
            if url:
                urls.append(url)
        return urls

    async def _resolve_previous_tail_frame_url(
        self,
        workflow_id: str,
        clip_index: int,
    ) -> str | None:
        """Return the selected tail-frame URL of (clip_index - 1)."""
        prev_clip_index = clip_index - 1
        result = await self.db.execute(
            select(BizStageVersion).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == prev_clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        prev_versions = result.scalars().all()
        if not prev_versions:
            return None
        url = self._find_keyframe_frame_url(prev_versions, prev_clip_index, "last")
        logger.info(
            "resolve_previous_tail_frame: clip=%d prev_clip=%d url=%s",
            clip_index, prev_clip_index, (url[:80] + "...") if url and len(url) > 80 else url,
        )
        return url or None

    async def generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate keyframe for a clip."""
        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            raise ValueError("角色设定图请使用 /character-sheets/{character_index}/generate 接口生成。")
        return await self._generate_keyframe(workflow_id, clip_index, owner_user_id=owner_user_id)

    async def generate_character_sheet(
        self,
        workflow_id: str,
        character_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a character sheet by 1-based character index."""
        if character_index <= 0:
            raise ValueError("角色序号必须从 1 开始。")
        clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + character_index
        return await self._generate_keyframe(workflow_id, clip_index, owner_user_id=owner_user_id)

    async def _generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a clip keyframe or a character sheet for internal workflow orchestration."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        storyboard_version = await self._selected_storyboard_version(wf)
        if storyboard_version is None:
            raise ValueError("请先选中一个分镜版本。")
        characters, clips = self._storyboard_plan(storyboard_version)
        is_character_sheet = clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE
        character: dict[str, Any] | None = None
        clip: dict[str, Any] | None = None
        if is_character_sheet:
            char_index = clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE - 1
            if char_index < 0 or char_index >= len(characters):
                raise ValueError("角色不存在，请重新选择分镜版本。")
            character = characters[char_index]
        else:
            clip = next((item for item in clips if safe_int(item.get("clipIndex"), 0) == clip_index), None)
            if clip is None:
                raise ValueError("镜头不存在，请重新选择分镜版本。")

        version_id = f"kv_{random_id()[:12]}"
        now = now_iso()

        # Count existing keyframe versions for this clip
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0
        width, height = _dimensions_from_aspect_ratio(wf.aspect_ratio)

        # Resolve character sheet URLs for reference (skip for character sheets themselves)
        character_sheet_urls: list[str] = []
        if not is_character_sheet:
            character_sheet_urls = await self._resolve_character_sheet_urls(workflow_id)

        # Reuse the previous clip's tail frame directly as this clip's start
        # frame. Do not generate a new start frame for clip 2+.
        # For clips after the first, require the previous clip's tail frame
        previous_tail_frame_url: str | None = None
        if not is_character_sheet and clip_index > 1:
            previous_tail_frame_url = await self._resolve_previous_tail_frame_url(
                workflow_id, clip_index,
            )
            if not previous_tail_frame_url:
                raise ValueError(
                    f"镜头 {clip_index} 的前一个镜头（镜头 {clip_index - 1}）"
                    f"缺少尾帧远程 URL，请先确保前一个镜头的关键帧已完整生成。"
                )

        if previous_tail_frame_url:
            prompt = self._generation_request_builder.keyframe_prompt(wf, clip or {})
            start_frame_output_url = previous_tail_frame_url
            start_frame_remote_url = previous_tail_frame_url
            start_frame_mime_type = "image/png"
            start_frame_width = width
            start_frame_height = height
            start_frame_run_id = ""
            start_frame_model_info: dict[str, Any] = {}
            start_frame_metadata: dict[str, Any] = {}
            start_frame_gen_result_id = ""
            logger.info(
                "Reusing previous tail frame as start frame for clip %s: %s",
                clip_index, previous_tail_frame_url[:80],
            )
        else:
            generation_request, prompt = self._generation_request_builder.build_keyframe_request(
                wf,
                workflow_id=workflow_id,
                clip_index=clip_index,
                width=width,
                height=height,
                character=character,
                clip=clip,
                character_sheet_urls=character_sheet_urls or None,
            )
            logger.info(
                "Generating start frame for clip %s (model=%s, char_sheets=%d)...",
                clip_index, wf.image_model, len(character_sheet_urls),
            )
            gen_result = await self._get_generation_service().create_run(generation_request)
            image_result = self._generation_result_parser.parse_image_result(
                gen_result,
                fallback_width=width,
                fallback_height=height,
            )
            start_frame_output_url = image_result.output_url
            start_frame_remote_url = image_result.remote_source_url or image_result.output_url
            start_frame_mime_type = image_result.mime_type
            start_frame_width = image_result.width
            start_frame_height = image_result.height
            start_frame_run_id = image_result.run_id
            start_frame_model_info = image_result.model_info
            start_frame_metadata = image_result.metadata
            start_frame_gen_result_id = gen_result.get("id") or image_result.run_id
            logger.info(
                "Start frame generated for clip %s: %s",
                clip_index, image_result.output_url[:80],
            )

        end_frame_remote_url = ""
        end_frame_output_url = ""
        if not is_character_sheet:
            # Generate end frame via image-to-image using start frame as reference.
            ref_url = start_frame_remote_url or start_frame_output_url
            if not ref_url:
                raise ValueError(f"镜头 {clip_index} 的首帧缺少远程 URL，无法生成尾帧。")

            for attempt in range(3):
                try:
                    end_request, _ = self._generation_request_builder.build_end_keyframe_request(
                        wf,
                        workflow_id=workflow_id,
                        clip_index=clip_index,
                        width=width,
                        height=height,
                        clip=clip,
                        start_frame_remote_url=ref_url,
                        character_sheet_urls=character_sheet_urls or None,
                    )
                    logger.info(
                        "Generating end frame for clip %s (attempt %d/3) with reference: %s...",
                        clip_index, attempt + 1, ref_url[:80],
                    )
                    end_gen_result = await self._get_generation_service().create_run(end_request)
                    end_image_result = self._generation_result_parser.parse_image_result(
                        end_gen_result,
                        fallback_width=width,
                        fallback_height=height,
                    )
                    end_frame_remote_url = end_image_result.remote_source_url or end_image_result.output_url
                    end_frame_output_url = end_image_result.output_url
                    logger.info("End frame generated for clip %s: %s", clip_index, end_frame_output_url[:80])
                    break
                except Exception as e:
                    if attempt < 2:
                        delay = 2 ** attempt
                        logger.warning(
                            "End frame generation failed for clip %s (attempt %d/3), retrying in %ds: %s",
                            clip_index, attempt + 1, delay, e,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "End frame generation failed for clip %s after 3 attempts: %s",
                            clip_index, e,
                        )
                        raise

        asset = self._row_factory.create_material_asset(
            wf=wf,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            media_type="image",
            title=(f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧"),
            public_url=start_frame_output_url,
            mime_type=start_frame_mime_type,
            width=start_frame_width,
            height=start_frame_height,
            duration_seconds=0,
            origin_provider=trim(start_frame_metadata.get("provider")),
            origin_model=trim(start_frame_metadata.get("providerModel")),
            remote_url=start_frame_remote_url,
            thumbnail_url=self._material_thumbnail_url("image", start_frame_output_url),
            metadata={
                "runId": start_frame_gen_result_id,
                "prompt": prompt,
                "remoteSourceUrl": start_frame_remote_url,
                "reusedPreviousTailFrame": bool(previous_tail_frame_url),
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
            },
        )
        self.db.add(asset)
        output_summary = {
            "fileUrl": start_frame_output_url,
            "previewUrl": start_frame_output_url,
            "width": start_frame_width,
            "height": start_frame_height,
            "prompt": prompt,
            "runId": start_frame_run_id,
            "remoteSourceUrl": start_frame_remote_url,
        }
        input_summary = {
            "clipIndex": clip_index,
            "prompt": prompt,
        }
        title = f"镜头 {clip_index} 关键帧 {version_count + 1}"
        if character is not None:
            output_summary.update({
                "sheetUrl": start_frame_output_url,
                "characterName": character.get("name", ""),
                "characterAppearance": character.get("appearance", ""),
            })
            input_summary.update({
                "variantKind": VARIANT_KIND_CHARACTER_SHEET,
                "characterName": character.get("name", ""),
                "appearance": character.get("appearance", ""),
            })
            title = f"{character.get('name')} 三视图 {version_count + 1}"
        else:
            end_frame_remote = end_frame_remote_url or end_frame_output_url
            output_summary.update({
                "startFrameUrl": start_frame_output_url,
                "endFrameUrl": end_frame_output_url,
                "startFrameRemoteUrl": start_frame_remote_url,
                "endFrameRemoteUrl": end_frame_remote,
                "selectedFirstFrame": True,
                "selectedLastFrame": True,
                "reusedPreviousTailFrame": bool(previous_tail_frame_url),
            })
            input_summary.update({
                "variantKind": "keyframe",
                "shotLabel": (clip or {}).get("shotLabel", ""),
                "scene": (clip or {}).get("scene", ""),
            })

        keyframe_version = self._row_factory.create_stage_version(
            wf=wf,
            stage_version_id=version_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=title,
            status="COMPLETED",
            selected=1,
            material_asset_id=asset.material_asset_id,
            preview_url=start_frame_output_url,
            download_url=start_frame_output_url,
            input_summary=input_summary,
            output_summary=output_summary,
            model_call_summary={
                "runId": start_frame_run_id,
                "modelInfo": start_frame_model_info,
            },
        )

        self.db.add(keyframe_version)
        await self._mark_selected_stage_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        wf.current_stage = STAGE_KEYFRAME if is_character_sheet else STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def generate_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a single keyframe frame (first or last).

        - frame_role="first": text-to-image, generates the start frame.
        - frame_role="last":  image-to-image using the existing first frame
          as reference, generates the end frame.
        """
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        if clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE:
            raise ValueError("角色设定图不支持首尾帧生成，请使用角色设定图生成接口。")

        storyboard_version = await self._selected_storyboard_version(wf)
        if storyboard_version is None:
            raise ValueError("请先选中一个分镜版本。")
        characters, clips = self._storyboard_plan(storyboard_version)
        is_character_sheet = clip_index >= CHARACTER_SHEET_CLIP_INDEX_BASE
        character: dict[str, Any] | None = None
        clip: dict[str, Any] | None = None
        if is_character_sheet:
            char_index = clip_index - CHARACTER_SHEET_CLIP_INDEX_BASE - 1
            if char_index < 0 or char_index >= len(characters):
                raise ValueError("角色不存在，请重新选择分镜版本。")
            character = characters[char_index]
        else:
            clip = next((item for item in clips if safe_int(item.get("clipIndex"), 0) == clip_index), None)
            if clip is None:
                raise ValueError("镜头不存在，请重新选择分镜版本。")

        version_id = f"fv_{random_id()[:12]}"
        now = now_iso()

        # Count existing keyframe versions for this clip
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0
        width, height = _dimensions_from_aspect_ratio(wf.aspect_ratio)

        normalized_role = trim(frame_role).lower()
        is_first = normalized_role in ("first", "start", "首帧")
        is_last = normalized_role in ("last", "end", "尾帧")

        if not is_first and not is_last:
            raise ValueError(f"不支持的 frame_role: {frame_role}，仅支持 first/last。")

        # Resolve character sheet URLs for reference (skip for character sheets themselves)
        character_sheet_urls: list[str] = []
        if not is_character_sheet:
            character_sheet_urls = await self._resolve_character_sheet_urls(workflow_id)

        # ---- Generate the image -------------------------------------------------
        prompt: str = ""
        reused_start_frame_url = ""
        if is_first:
            # Reuse previous clip's tail frame directly as this clip's start
            # frame. Do not generate a new start frame for clip 2+.
            previous_tail_frame_url: str | None = None
            if not is_character_sheet and clip_index > 1:
                previous_tail_frame_url = await self._resolve_previous_tail_frame_url(
                    workflow_id, clip_index,
                )
                if not previous_tail_frame_url:
                    raise ValueError(
                        f"镜头 {clip_index} 的前一个镜头（镜头 {clip_index - 1}）"
                        f"缺少已选尾帧 URL，请先生成并选中前一个镜头的尾帧。"
                    )

            if previous_tail_frame_url:
                prompt = self._generation_request_builder.keyframe_prompt(wf, clip or {})
                reused_start_frame_url = previous_tail_frame_url
                logger.info(
                    "Reusing previous tail frame as start frame for clip %s: %s",
                    clip_index, previous_tail_frame_url[:80],
                )
            else:
                logger.info(
                    "Generating start frame for clip %s (model=%s, frame_role=%s, char_sheets=%d)...",
                    clip_index, wf.image_model, frame_role, len(character_sheet_urls),
                )
                generation_request, prompt = self._generation_request_builder.build_keyframe_request(
                    wf,
                    workflow_id=workflow_id,
                    clip_index=clip_index,
                    width=width,
                    height=height,
                    character=character,
                    clip=clip,
                    character_sheet_urls=character_sheet_urls or None,
                )
        else:
            # Find an existing first-frame remote URL to use as reference
            versions = await self._list_stage_versions(workflow_id)
            start_frame_remote_url = self._find_first_frame_remote_url(versions, clip_index)
            if not start_frame_remote_url:
                raise ValueError("未找到该镜头的首帧远端 URL，请先生成首帧后再生成尾帧。")

            logger.info(
                "Generating end frame for clip %s (model=%s, frame_role=%s, ref=%s, char_sheets=%d)...",
                clip_index, wf.image_model, frame_role, start_frame_remote_url[:80], len(character_sheet_urls),
            )
            generation_request, prompt = self._generation_request_builder.build_end_keyframe_request(
                wf,
                workflow_id=workflow_id,
                clip_index=clip_index,
                width=width,
                height=height,
                clip=clip,
                start_frame_remote_url=start_frame_remote_url,
                character_sheet_urls=character_sheet_urls or None,
            )

        if reused_start_frame_url:
            image_output_url = reused_start_frame_url
            image_remote_url = reused_start_frame_url
            image_mime_type = "image/png"
            image_width = width
            image_height = height
            image_run_id = ""
            image_model_info: dict[str, Any] = {}
            image_metadata: dict[str, Any] = {}
            gen_result_id = ""
        else:
            gen_result = await self._get_generation_service().create_run(generation_request)
            image_result = self._generation_result_parser.parse_image_result(
                gen_result,
                fallback_width=width,
                fallback_height=height,
            )
            image_output_url = image_result.output_url
            image_remote_url = image_result.remote_source_url or image_result.output_url
            image_mime_type = image_result.mime_type
            image_width = image_result.width
            image_height = image_result.height
            image_run_id = image_result.run_id
            image_model_info = image_result.model_info
            image_metadata = image_result.metadata
            gen_result_id = gen_result.get("id") or image_result.run_id
            logger.info(
                "%s frame generated for clip %s: %s",
                "Start" if is_first else "End", clip_index, image_result.output_url[:80],
            )

        # ---- Persist ------------------------------------------------------------
        asset = self._row_factory.create_material_asset(
            wf=wf,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            media_type="image",
            title=(f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧-{frame_role}"),
            public_url=image_output_url,
            mime_type=image_mime_type,
            width=image_width,
            height=image_height,
            duration_seconds=0,
            origin_provider=trim(image_metadata.get("provider")),
            origin_model=trim(image_metadata.get("providerModel")),
            remote_url=image_remote_url,
            thumbnail_url=self._material_thumbnail_url("image", image_output_url),
            metadata={
                "runId": gen_result_id,
                "prompt": prompt,
                "remoteSourceUrl": image_remote_url,
                "reusedPreviousTailFrame": bool(reused_start_frame_url),
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
                "frameRole": frame_role,
            },
        )
        self.db.add(asset)

        output_summary: dict[str, Any] = {
            "fileUrl": image_output_url,
            "previewUrl": image_output_url,
            "width": image_width,
            "height": image_height,
            "prompt": prompt,
            "runId": image_run_id,
            "remoteSourceUrl": image_remote_url,
            "frameRole": frame_role,
        }
        input_summary: dict[str, Any] = {
            "clipIndex": clip_index,
            "prompt": prompt,
            "frameRole": frame_role,
        }
        if character is not None:
            output_summary.update({
                "sheetUrl": image_output_url,
                "characterName": character.get("name", ""),
                "characterAppearance": character.get("appearance", ""),
            })
            input_summary.update({
                "variantKind": VARIANT_KIND_CHARACTER_SHEET,
                "characterName": character.get("name", ""),
                "appearance": character.get("appearance", ""),
            })
        elif is_first:
            output_summary.update({
                "startFrameUrl": image_output_url,
                "startFrameRemoteUrl": image_remote_url,
                "selectedFirstFrame": True,
                "reusedPreviousTailFrame": bool(reused_start_frame_url),
            })
            input_summary.update({
                "variantKind": "keyframe",
                "shotLabel": (clip or {}).get("shotLabel", ""),
                "scene": (clip or {}).get("scene", ""),
            })
        else:
            output_summary.update({
                "endFrameUrl": image_output_url,
                "endFrameRemoteUrl": image_remote_url,
                "selectedLastFrame": True,
            })
            input_summary.update({
                "variantKind": "keyframe_end",
                "shotLabel": (clip or {}).get("shotLabel", ""),
                "scene": (clip or {}).get("scene", ""),
            })

        frame_version = self._row_factory.create_stage_version(
            wf=wf,
            stage_version_id=version_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=(f"{character.get('name')} 三视图 {version_count + 1}" if character
                   else f"镜头 {clip_index} 关键帧 {frame_role} {version_count + 1}"),
            status="COMPLETED",
            selected=0,
            material_asset_id=asset.material_asset_id,
            preview_url=image_output_url,
            download_url=image_output_url,
            input_summary=input_summary,
            output_summary=output_summary,
            model_call_summary={
                "runId": image_run_id,
                "modelInfo": image_model_info,
            },
        )
        self.db.add(frame_version)
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Select a keyframe version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Select a keyframe frame."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None or version.clip_index != clip_index:
            return None
        input_summary = _read_json(version.input_summary_json)
        if trim(input_summary.get("variantKind")) == VARIANT_KIND_CHARACTER_SHEET:
            raise ValueError("角色三视图不支持选择首帧/尾帧。")

        normalized_role = trim(frame_role).lower()
        is_first = normalized_role in ("first", "start", "首帧")
        is_last = normalized_role in ("last", "end", "尾帧")
        if not is_first and not is_last:
            raise ValueError(f"不支持的 frame_role: {frame_role}，仅支持 first/last。")

        selection_key = "selectedFirstFrame" if is_first else "selectedLastFrame"
        url = self._keyframe_frame_url(_read_json(version.output_summary_json), "first" if is_first else "last")
        if not url:
            label = "首帧" if is_first else "尾帧"
            raise ValueError(f"所选版本缺少{label} URL。")

        versions = await self._list_stage_versions(workflow_id)
        now = now_iso()
        for item in versions:
            if item.stage_type != STAGE_KEYFRAME or item.clip_index != clip_index:
                continue
            if self._is_character_sheet_version(item):
                continue
            output = _read_json(item.output_summary_json)
            if output.get(selection_key) is True or item.stage_version_id == version_id:
                output[selection_key] = item.stage_version_id == version_id
                item.output_summary_json = _write_json(output)
                item.update_time = now
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_character_sheet_asset(
        self,
        workflow_id: str,
        clip_index: int,
        asset_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Link a character sheet material asset to a workflow clip."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None

        # Update the workflow with the selected asset
        now = now_iso()
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate video for a clip."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        storyboard_version = await self._selected_storyboard_version(wf)
        if storyboard_version is None:
            raise ValueError("请先选中一个分镜版本。")
        _, clips = self._storyboard_plan(storyboard_version)
        clip = next((item for item in clips if safe_int(item.get("clipIndex"), 0) == clip_index), None)
        if clip is None:
            raise ValueError("镜头不存在，请重新选择分镜版本。")
        versions = await self._list_stage_versions(workflow_id)
        keyframe_versions = [
            v for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and v.clip_index == clip_index
            and not self._is_character_sheet_version(v)
        ]
        selected_keyframe = next((v for v in keyframe_versions if v.selected == 1), None)
        if not keyframe_versions:
            raise ValueError("请先为该镜头生成并选中关键帧。")
        first_frame_url = self._find_keyframe_frame_url(keyframe_versions, clip_index, "first")
        last_frame_url = self._find_keyframe_frame_url(keyframe_versions, clip_index, "last")
        if not first_frame_url:
            raise ValueError("关键帧缺少远端首帧图片 URL，无法生成视频。")
        model_first_frame_url = self._video_frame_model_input(first_frame_url)
        model_last_frame_url = self._video_frame_model_input(last_frame_url) if last_frame_url else ""
        if not model_first_frame_url:
            raise ValueError("关键帧远端首帧图片 URL 不是视频模型可访问的地址，无法生成视频。")

        version_id = f"vv_{random_id()[:12]}"
        now = now_iso()

        # Count existing video versions for this clip
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_VIDEO,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0
        width, height = _dimensions_from_size(wf.video_size, wf.aspect_ratio)
        duration_seconds = safe_int(clip.get("targetDurationSeconds"), wf.min_duration_seconds or 8)
        duration_seconds = max(1, min(duration_seconds, wf.max_duration_seconds or duration_seconds))
        generation_request, prompt = self._generation_request_builder.build_video_request(
            wf,
            workflow_id=workflow_id,
            clip_index=clip_index,
            clip=clip,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            first_frame_url=model_first_frame_url,
            last_frame_url=model_last_frame_url,
        )
        gen_result = await self._get_generation_service().create_run(generation_request)
        video_result = self._generation_result_parser.parse_video_result(
            gen_result,
            fallback_preview_url=first_frame_url,
            fallback_width=width,
            fallback_height=height,
            fallback_duration_seconds=duration_seconds,
        )
        asset_id = ""
        if video_result.output_url:
            asset = self._row_factory.create_material_asset(
                wf=wf,
                stage_type=STAGE_VIDEO,
                clip_index=clip_index,
                version_no=version_count + 1,
                media_type="video",
                title=f"镜头 {clip_index} 视频",
                public_url=video_result.output_url,
                mime_type=video_result.mime_type,
                width=video_result.width,
                height=video_result.height,
                duration_seconds=video_result.duration_seconds,
                origin_provider=trim(video_result.metadata.get("provider")),
                origin_model=trim(video_result.metadata.get("providerModel")),
                remote_task_id=video_result.remote_task_id,
                thumbnail_url=self._material_thumbnail_url(
                    "video",
                    video_result.output_url,
                    [video_result.preview_url, first_frame_url, last_frame_url],
                ),
                metadata={
                    "runId": video_result.run_id,
                    "prompt": prompt,
                    "clip": clip,
                },
            )
            self.db.add(asset)
            asset_id = asset.material_asset_id

        video_version = self._row_factory.create_stage_version(
            wf=wf,
            stage_version_id=version_id,
            stage_type=STAGE_VIDEO,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=f"镜头 {clip_index} 视频 {version_count + 1}",
            status="COMPLETED" if video_result.output_url else video_result.status,
            selected=1 if video_result.output_url else 0,
            parent_version_id=selected_keyframe.stage_version_id if selected_keyframe else "",
            material_asset_id=asset_id,
            preview_url=video_result.preview_url,
            download_url=video_result.output_url,
            input_summary={
                "clipIndex": clip_index,
                "prompt": prompt,
                "firstFrameUrl": first_frame_url,
                "lastFrameUrl": last_frame_url,
            },
            output_summary={
                "fileUrl": video_result.output_url,
                "previewUrl": video_result.preview_url,
                "posterUrl": first_frame_url,
                "taskId": video_result.remote_task_id,
                "taskStatus": video_result.metadata.get("taskStatus", video_result.status),
                "durationSeconds": duration_seconds,
                "width": width,
                "height": height,
                "prompt": prompt,
                "runId": video_result.run_id,
            },
            model_call_summary={
                "runId": video_result.run_id,
                "modelInfo": video_result.model_info,
            },
        )

        self.db.add(video_version)
        if video_result.output_url:
            await self._mark_selected_stage_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
            wf.current_stage = STAGE_JOINED
        else:
            wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now
        await self.db.commit()

        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def select_video(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Select a video version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_READY
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Finalize
    # ------------------------------------------------------------------

    async def finalize_workflow(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Mark workflow completed with concatenated selected videos as final output.

        When ``self._media_service`` is available and there are multiple
        selected videos, downloads them and concatenates via ffmpeg.
        Falls back to using the first selected video as the preview when
        the media service is unavailable or concatenation fails.
        """
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        selected_videos = [
            v for v in versions
            if v.stage_type == STAGE_VIDEO and v.selected == 1 and trim(v.preview_url)
        ]
        if not selected_videos:
            raise ValueError("请先为每个镜头选中视频版本。")
        selected_videos.sort(key=lambda v: v.clip_index)

        total_duration = sum(
            safe_float(_read_json(v.output_summary_json).get("durationSeconds"), 0.0)
            for v in selected_videos
        )

        joined_url = ""
        joined_note = ""

        # Attempt real concatenation via the media service
        if self._media_service is not None and len(selected_videos) > 1:
            try:
                local_urls: list[str] = []
                for v in selected_videos:
                    source_url = trim(v.download_url) or trim(v.preview_url)
                    if not source_url:
                        continue
                    stored = self._media_service.materialize_artifact(
                        source_url,
                        f"tasks/{workflow_id}/clips",
                        f"clip_{v.clip_index}.mp4",
                    )
                    local_url = (
                        stored.public_url
                        if hasattr(stored, "public_url")
                        else source_url
                    )
                    local_urls.append(local_url)

                if len(local_urls) >= 2:
                    joined = self._media_service.concat_videos(
                        f"tasks/{workflow_id}/joined",
                        f"joined_{workflow_id}.mp4",
                        local_urls,
                    )
                    joined_url = (
                        joined.public_url
                        if hasattr(joined, "public_url")
                        else ""
                    )
                    joined_note = "已完成视频拼接。"

                if joined_url:
                    logger.info(
                        "Workflow %s: videos concatenated successfully → %s",
                        workflow_id, joined_url,
                    )
            except Exception as exc:
                logger.warning(
                    "Workflow %s: video concatenation failed, falling back to preview: %s",
                    workflow_id, exc,
                )

        if joined_url:
            public_url = joined_url
            metadata_note = joined_note or "已拼接所有选中视频片段。"
        else:
            first = selected_videos[0]
            public_url = first.download_url or first.preview_url
            metadata_note = (
                "当前环境使用首个已选视频作为成片预览"
                if len(selected_videos) <= 1
                else "拼接失败，使用首个已选视频作为成片预览。请检查 ffmpeg 是否可用。"
            )

        asset = self._row_factory.create_material_asset(
            wf=wf,
            stage_type=STAGE_JOINED,
            clip_index=0,
            version_no=1,
            media_type="video",
            title=f"{wf.title} 完整视频",
            public_url=public_url,
            mime_type="video/mp4",
            width=0,
            height=0,
            duration_seconds=total_duration,
            thumbnail_url=self._material_thumbnail_url("video", public_url),
            metadata={
                "sourceVideoVersionIds": [v.stage_version_id for v in selected_videos],
                "note": metadata_note,
            },
        )
        self.db.add(asset)
        wf.final_join_asset_id = asset.material_asset_id
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_COMPLETED
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Ratings & cleanup
    # ------------------------------------------------------------------

    async def rate_workflow(
        self,
        workflow_id: str,
        rating: int,
        note: str = "",
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Rate a workflow (1-5)."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        wf.effect_rating = rating
        wf.effect_rating_note = note
        wf.rated_at = now_iso()
        wf.update_time = now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def rate_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        rating: int,
        note: str = "",
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Rate a stage version."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, "")
        if version is None:
            return None
        version.rating = rating
        version.rating_note = note
        version.rated_at = now_iso()
        version.update_time = now_iso()
        if version.material_asset_id:
            asset = await self._find_asset(version.material_asset_id)
            if asset is not None:
                asset.user_rating = rating
                asset.rating_note = note
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def delete_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Delete a stage version and its downstream selections."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        target = await self._require_stage_version(workflow_id, version_id, "")
        if target is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        to_delete = self._resolve_delete_version_chain(target, versions)
        now = now_iso()
        for v in to_delete:
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
            if v.material_asset_id:
                await self._mark_asset_deleted(v.material_asset_id)
        wf.update_time = now
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    async def delete_all_stage_versions(
        self,
        workflow_id: str,
        owner_user_id: int | None = None,
        stage_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Delete all non-deleted stage versions for a workflow, optionally filtered by stage type."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        if stage_type:
            versions = [v for v in versions if v.stage_type == stage_type]
        if not versions:
            return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)
        now = now_iso()
        for v in versions:
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
            if v.material_asset_id:
                await self._mark_asset_deleted(v.material_asset_id)
        wf.update_time = now
        # Recompute current_stage from remaining versions so the workflow
        # state stays consistent for auto-pilot and UI stage detection.
        wf.current_stage = await self._compute_current_stage(workflow_id)
        await self.db.commit()
        return await self.get_workflow(workflow_id, owner_user_id=owner_user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        stmt = select(BizStageWorkflow).where(*filters)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _require_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        expected_stage_type: str,
    ) -> BizStageVersion | None:
        stmt = select(BizStageVersion).where(
            BizStageVersion.workflow_id == workflow_id,
            BizStageVersion.stage_version_id == version_id,
            BizStageVersion.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            return None
        if expected_stage_type and version.stage_type != expected_stage_type:
            return None
        return version

    async def _find_asset(self, asset_id: str) -> BizMaterialAsset | None:
        stmt = select(BizMaterialAsset).where(
            BizMaterialAsset.material_asset_id == asset_id,
            BizMaterialAsset.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _compute_current_stage(self, workflow_id: str) -> str:
        """Derive current_stage from remaining non-deleted versions.

        The stage represents the next step to work on, following the
        same progression as the auto-pilot: storyboard → keyframe → video → joined.
        """
        remaining = await self._list_stage_versions(workflow_id)
        if not remaining:
            return STAGE_STORYBOARD

        has_storyboard = any(v.stage_type == STAGE_STORYBOARD for v in remaining)
        has_selected_storyboard = any(
            v.stage_type == STAGE_STORYBOARD and v.selected for v in remaining
        )
        has_keyframe = any(v.stage_type == STAGE_KEYFRAME for v in remaining)
        has_selected_keyframe = any(
            v.stage_type == STAGE_KEYFRAME and v.selected for v in remaining
        )
        has_video = any(v.stage_type == STAGE_VIDEO for v in remaining)
        has_selected_video = any(
            v.stage_type == STAGE_VIDEO and v.selected for v in remaining
        )

        if has_selected_video:
            return STAGE_JOINED
        if has_video or has_selected_keyframe:
            return STAGE_VIDEO
        if has_keyframe or has_selected_storyboard:
            return STAGE_KEYFRAME
        if has_storyboard:
            return STAGE_STORYBOARD
        return STAGE_STORYBOARD

    @staticmethod
    def _find_first_frame_remote_url(
        versions: list[BizStageVersion],
        clip_index: int,
    ) -> str:
        """Find the first-frame remote URL from selected keyframe versions for a clip.

        Checks selected keyframe versions first (those with startFrameRemoteUrl
        or remoteSourceUrl), then falls back to any keyframe version for the clip.
        """
        keyframe_versions = [
            v for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and v.clip_index == clip_index
        ]
        # Prefer selected versions
        for v in sorted(keyframe_versions, key=lambda x: 0 if x.selected else 1):
            output = _read_json(v.output_summary_json)
            url = first_non_blank(
                trim(output.get("startFrameRemoteUrl")),
                trim(output.get("remoteSourceUrl")),
            )
            if url:
                return url
        return ""

    @staticmethod
    def _is_character_sheet_version(version: BizStageVersion) -> bool:
        return trim(_read_json(version.input_summary_json).get("variantKind")) == VARIANT_KIND_CHARACTER_SHEET

    @staticmethod
    def _keyframe_frame_url(output: dict[str, Any], frame_role: str) -> str:
        normalized_role = trim(frame_role).lower()
        stored_role = trim(output.get("frameRole")).lower()
        if normalized_role in ("last", "end", "尾帧"):
            return first_non_blank(
                trim(output.get("endFrameRemoteUrl")),
                trim(output.get("lastFrameRemoteUrl")),
                trim(output.get("endFrameUrl")),
                trim(output.get("lastFrameUrl")),
                trim(output.get("remoteSourceUrl")) if stored_role in ("last", "end", "尾帧") else "",
                trim(output.get("fileUrl")) if stored_role in ("last", "end", "尾帧") else "",
            )
        return first_non_blank(
            trim(output.get("startFrameRemoteUrl")),
            trim(output.get("firstFrameRemoteUrl")),
            trim(output.get("startFrameUrl")),
            trim(output.get("firstFrameUrl")),
            trim(output.get("remoteSourceUrl")) if stored_role in ("first", "start", "首帧") else "",
            trim(output.get("fileUrl")) if stored_role in ("first", "start", "首帧") else "",
        )

    def _find_keyframe_frame_url(
        self,
        versions: list[BizStageVersion],
        clip_index: int,
        frame_role: str,
    ) -> str:
        normalized_role = trim(frame_role).lower()
        selection_key = (
            "selectedLastFrame"
            if normalized_role in ("last", "end", "尾帧")
            else "selectedFirstFrame"
        )
        candidates = [
            v for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and v.clip_index == clip_index
            and not self._is_character_sheet_version(v)
        ]
        for version in candidates:
            output = _read_json(version.output_summary_json)
            if output.get(selection_key) is True:
                url = self._keyframe_frame_url(output, frame_role)
                if url:
                    return url
        for version in candidates:
            if version.selected != 1:
                continue
            url = self._keyframe_frame_url(_read_json(version.output_summary_json), frame_role)
            if url:
                return url
        for version in candidates:
            url = self._keyframe_frame_url(_read_json(version.output_summary_json), frame_role)
            if url:
                return url
        return ""

    async def _mark_asset_deleted(self, asset_id: str) -> None:
        if not asset_id:
            return
        stmt = (
            update(BizMaterialAsset)
            .where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.is_deleted == 0,
            )
            .values(selected_for_next=0, is_deleted=1, update_time=now_iso())
        )
        await self.db.execute(stmt)

    async def _list_stage_versions(self, workflow_id: str) -> list[BizStageVersion]:
        stmt = (
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
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _refresh_video_versions(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> bool:
        changed = False
        now = now_iso()
        for version in versions:
            if version.stage_type != STAGE_VIDEO or version.is_deleted != 0:
                continue
            status = trim(version.status).upper()
            if status == "COMPLETED" and trim(version.download_url):
                continue
            output_summary = _read_json(version.output_summary_json)
            run_id = trim(output_summary.get("runId")) or trim(_read_json(version.model_call_summary_json).get("runId"))
            if not run_id:
                continue
            try:
                run = await self._get_generation_service().get_run(run_id)
            except Exception:  # noqa: S112 — best-effort run lookup
                continue
            try:
                refresh_result = self._generation_result_parser.parse_video_refresh_result(
                    run or {},
                    output_summary=output_summary,
                    current_status=status,
                )
            except ValueError:
                continue

            if refresh_result.output_url:
                asset_id = version.material_asset_id
                if not asset_id:
                    asset = self._row_factory.create_material_asset(
                        wf=wf,
                        stage_type=STAGE_VIDEO,
                        clip_index=safe_int(version.clip_index, 0),
                        version_no=safe_int(version.version_no, 1),
                        media_type="video",
                        title=version.title or f"镜头 {version.clip_index} 视频",
                        public_url=refresh_result.output_url,
                        mime_type=refresh_result.mime_type,
                        width=refresh_result.width,
                        height=refresh_result.height,
                        duration_seconds=refresh_result.duration_seconds,
                        origin_provider=refresh_result.origin_provider,
                        origin_model=refresh_result.origin_model,
                        remote_task_id=refresh_result.remote_task_id,
                        remote_url=refresh_result.remote_source_url,
                        thumbnail_url=self._material_thumbnail_url("video", refresh_result.output_url),
                        metadata={
                            "runId": run_id,
                            "taskId": refresh_result.remote_task_id,
                            "taskStatus": refresh_result.task_status,
                            "remoteSourceUrl": refresh_result.remote_source_url,
                        },
                    )
                    self.db.add(asset)
                    asset_id = asset.material_asset_id
                output_summary.update({
                    "fileUrl": refresh_result.output_url,
                    "previewUrl": refresh_result.output_url,
                    "taskStatus": refresh_result.task_status or "COMPLETED",
                    "remoteSourceUrl": refresh_result.remote_source_url,
                })
                version.status = "COMPLETED"
                version.selected = 1
                version.material_asset_id = asset_id
                version.preview_url = refresh_result.output_url
                version.download_url = refresh_result.output_url
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                await self._mark_selected_stage_version(wf.workflow_id, STAGE_VIDEO, safe_int(version.clip_index, 0), version.stage_version_id)
                wf.current_stage = STAGE_JOINED
                wf.status = STATUS_READY
                wf.update_time = now
                changed = True
                continue

            if refresh_result.run_status in {"failed", "error"}:
                output_summary["taskStatus"] = refresh_result.task_status or "FAILED"
                output_summary["error"] = refresh_result.error
                version.status = "FAILED"
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                changed = True
            elif refresh_result.task_status:
                output_summary["taskStatus"] = refresh_result.task_status
                version.output_summary_json = _write_json(output_summary)
                version.update_time = now
                changed = True

        if changed:
            await self.db.commit()
        return changed

    async def _mark_selected_stage_version(
        self,
        workflow_id: str,
        stage_type: str,
        clip_index: int,
        selected_version_id: str,
    ) -> None:
        stmt = select(BizStageVersion).where(
            BizStageVersion.workflow_id == workflow_id,
            BizStageVersion.stage_type == stage_type,
            BizStageVersion.clip_index == clip_index,
            BizStageVersion.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        versions = result.scalars().all()
        now = now_iso()
        for v in versions:
            v.selected = 1 if v.stage_version_id == selected_version_id else 0
            v.update_time = now

    async def _selected_storyboard_version(self, wf: BizStageWorkflow) -> BizStageVersion | None:
        version_id = trim(wf.selected_storyboard_version_id)
        versions = await self._list_stage_versions(wf.workflow_id)
        storyboards = [v for v in versions if v.stage_type == STAGE_STORYBOARD]
        if version_id:
            for version in storyboards:
                if version.stage_version_id == version_id:
                    return version
        selected = next((v for v in storyboards if v.selected == 1), None)
        if selected is not None:
            return selected
        return storyboards[0] if storyboards else None

    def _storyboard_plan(self, version: BizStageVersion | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if version is None:
            return [], []
        output = _read_json(version.output_summary_json)
        script = trim(output.get("scriptMarkdown") or output.get("previewText"))
        return parse_workflow_storyboard_markdown(script).to_view()

    @staticmethod
    def _video_frame_model_input(public_url: str) -> str:
        normalized = trim(public_url)
        if normalized.startswith(("http://", "https://")):
            return normalized
        return ""

    async def _load_asset_map(
        self,
        versions: list[BizStageVersion],
        final_join_asset_id: str | None,
    ) -> dict[str, BizMaterialAsset]:
        asset_ids: set[str] = set()
        for v in versions:
            if v.material_asset_id:
                asset_ids.add(v.material_asset_id)
        if final_join_asset_id:
            asset_ids.add(final_join_asset_id)
        if not asset_ids:
            return {}
        stmt = select(BizMaterialAsset).where(
            BizMaterialAsset.material_asset_id.in_(asset_ids),
            BizMaterialAsset.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        assets = result.scalars().all()
        return {a.material_asset_id: a for a in assets}

    async def _require_material_asset(
        self,
        asset_id: str,
        owner_user_id: int,
    ) -> BizMaterialAsset | None:
        stmt = select(BizMaterialAsset).where(
            BizMaterialAsset.material_asset_id == asset_id,
            BizMaterialAsset.owner_user_id == owner_user_id,
            BizMaterialAsset.is_deleted == 0,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _resolve_delete_version_chain(
        self,
        target: BizStageVersion,
        versions: list[BizStageVersion],
    ) -> list[BizStageVersion]:
        deleted: list[BizStageVersion] = [target]
        if target.stage_type == STAGE_STORYBOARD:
            for v in versions:
                if v.stage_type == STAGE_KEYFRAME and v.parent_version_id == target.stage_version_id:
                    deleted.append(v)
            kf_ids = {v.stage_version_id for v in deleted if v.stage_type == STAGE_KEYFRAME}
            for v in versions:
                if v.stage_type == STAGE_VIDEO and v.parent_version_id in kf_ids:
                    deleted.append(v)
        elif target.stage_type == STAGE_KEYFRAME:
            for v in versions:
                if v.stage_type == STAGE_VIDEO and v.parent_version_id == target.stage_version_id:
                    deleted.append(v)
        seen: dict[str, BizStageVersion] = {}
        for v in deleted:
            seen[v.stage_version_id] = v
        return list(seen.values())
