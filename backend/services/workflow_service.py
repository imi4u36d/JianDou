"""Workflow service — Python translation of WorkflowApplicationService (Java).

Handles the multi-stage creative workflow lifecycle:
  STORYBOARD -> KEYFRAME -> VIDEO -> JOINED
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import WorkflowStage, WorkflowStatus
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

    def __init__(self, db: AsyncSession, generation_service: Any | None = None) -> None:
        self.db = db
        self._generation_service = generation_service
        self._view_mapper = WorkflowViewMapper(self._storyboard_plan)
        self._generation_request_builder = WorkflowGenerationRequestBuilder()
        self._generation_result_parser = WorkflowGenerationResultParser()
        self._row_factory = WorkflowPersistenceRowFactory()

    def _get_generation_service(self):
        if self._generation_service is None:
            raise RuntimeError("generation service not configured")
        return self._generation_service

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
        image_model = trim(request.get("imageModel"), "")
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
            style_preset=trim(request.get("stylePreset"), "cinematic"),
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
            style_preset="cinematic",
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
    ) -> list[dict[str, Any]]:
        """List user's workflows with version counts."""
        stmt = (
            select(BizStageWorkflow)
            .where(BizStageWorkflow.is_deleted == 0)
            .order_by(BizStageWorkflow.update_time.desc())
        )
        if owner_user_id is not None:
            stmt = stmt.where(BizStageWorkflow.owner_user_id == owner_user_id)
        result = await self.db.execute(stmt)
        workflows = result.scalars().all()

        rows: list[dict[str, Any]] = []
        for wf in workflows:
            versions = await self._list_stage_versions(wf.workflow_id)
            rows.append(self._view_mapper.to_workflow_summary(wf, versions))
        return rows

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
        image_model = trim(request.get("imageModel"), "")
        video_model = trim(request.get("videoModel"), "")
        await self._validate_generation_models(wf.owner_user_id, text_model, image_model, video_model)
        wf.aspect_ratio = aspect_ratio
        wf.style_preset = trim(request.get("stylePreset"), "cinematic")
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

    async def generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate keyframe for a clip."""
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
        generation_request, prompt = self._generation_request_builder.build_keyframe_request(
            wf,
            workflow_id=workflow_id,
            clip_index=clip_index,
            width=width,
            height=height,
            character=character,
            clip=clip,
        )
        gen_result = await self._get_generation_service().create_run(generation_request)
        image_result = self._generation_result_parser.parse_image_result(
            gen_result,
            fallback_width=width,
            fallback_height=height,
        )
        asset = self._row_factory.create_material_asset(
            wf=wf,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            media_type="image",
            title=(f"{character.get('name')} 三视图" if character else f"镜头 {clip_index} 关键帧"),
            public_url=image_result.output_url,
            mime_type=image_result.mime_type,
            width=image_result.width,
            height=image_result.height,
            duration_seconds=0,
            origin_provider=trim(image_result.metadata.get("provider")),
            origin_model=trim(image_result.metadata.get("providerModel")),
            remote_url=image_result.remote_source_url,
            metadata={
                "runId": gen_result.get("id") or image_result.run_id,
                "prompt": prompt,
                "remoteSourceUrl": image_result.remote_source_url,
                "characterName": character.get("name") if character else "",
                "clip": clip or {},
            },
        )
        self.db.add(asset)
        output_summary = {
            "fileUrl": image_result.output_url,
            "previewUrl": image_result.output_url,
            "width": image_result.width,
            "height": image_result.height,
            "prompt": prompt,
            "runId": image_result.run_id,
            "remoteSourceUrl": image_result.remote_source_url,
        }
        input_summary = {
            "clipIndex": clip_index,
            "prompt": prompt,
        }
        title = f"关键帧 {clip_index + 1}-{version_count + 1}"
        if character is not None:
            output_summary.update({
                "sheetUrl": image_result.output_url,
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
            output_summary.update({
                "startFrameUrl": image_result.output_url,
                "endFrameUrl": image_result.output_url,
                "startFrameRemoteUrl": image_result.remote_source_url,
                "endFrameRemoteUrl": image_result.remote_source_url,
                "selectedFirstFrame": True,
                "selectedLastFrame": True,
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
            preview_url=image_result.output_url,
            download_url=image_result.output_url,
            input_summary=input_summary,
            output_summary=output_summary,
            model_call_summary={
                "runId": image_result.run_id,
                "modelInfo": image_result.model_info,
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
        """Generate single keyframe frame."""
        wf = await self._require_workflow(workflow_id, owner_user_id)
        if wf is None:
            return None

        # Create a placeholder frame version
        version_id = f"fv_{random_id()[:12]}"

        # Count existing versions for this clip and frame role
        result = await self.db.execute(
            select(func.count()).where(
                BizStageVersion.workflow_id == workflow_id,
                BizStageVersion.stage_type == STAGE_KEYFRAME,
                BizStageVersion.clip_index == clip_index,
                BizStageVersion.is_deleted == 0,
            )
        )
        version_count = result.scalar() or 0

        frame_version = self._row_factory.create_stage_version(
            wf=wf,
            stage_version_id=version_id,
            stage_type=STAGE_KEYFRAME,
            clip_index=clip_index,
            version_no=version_count + 1,
            title=f"关键帧 {clip_index + 1}-{frame_role}",
            status="COMPLETED",
            selected=0,
            input_summary={"clipIndex": clip_index, "frameRole": frame_role},
            output_summary={"message": "关键帧帧生成中，请稍后刷新查看结果。"},
        )

        self.db.add(frame_version)
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
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = now_iso()
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
        selected_keyframe = next(
            (
                v for v in versions
                if v.stage_type == STAGE_KEYFRAME
                and v.clip_index == clip_index
                and v.selected == 1
                and trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
            ),
            None,
        )
        if selected_keyframe is None:
            raise ValueError("请先为该镜头生成并选中关键帧。")
        keyframe_output = _read_json(selected_keyframe.output_summary_json)
        first_frame_url = first_non_blank(
            trim(keyframe_output.get("startFrameRemoteUrl")),
            trim(keyframe_output.get("remoteSourceUrl")),
            trim(keyframe_output.get("remoteUrl")),
        )
        last_frame_url = first_non_blank(
            trim(keyframe_output.get("endFrameRemoteUrl")),
            trim(keyframe_output.get("remoteSourceUrl")),
            trim(keyframe_output.get("remoteUrl")),
        )
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
            title=f"视频 {clip_index + 1}-{version_count + 1}",
            status="COMPLETED" if video_result.output_url else video_result.status,
            selected=1 if video_result.output_url else 0,
            parent_version_id=selected_keyframe.stage_version_id,
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
        """Mark workflow completed with the selected videos as final output."""
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
        first = selected_videos[0]
        asset = self._row_factory.create_material_asset(
            wf=wf,
            stage_type=STAGE_JOINED,
            clip_index=0,
            version_no=1,
            media_type="video",
            title=f"{wf.title} 完整视频",
            public_url=first.download_url or first.preview_url,
            mime_type="video/mp4",
            width=0,
            height=0,
            duration_seconds=sum(safe_float(_read_json(v.output_summary_json).get("durationSeconds"), 0.0) for v in selected_videos),
            metadata={
                "sourceVideoVersionIds": [v.stage_version_id for v in selected_videos],
                "note": "当前环境使用首个已选视频作为成片预览，真实拼接服务接入后会生成完整拼接文件。",
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
