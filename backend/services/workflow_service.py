"""Workflow service — Python translation of WorkflowApplicationService (Java).

Handles the multi-stage creative workflow lifecycle:
  STORYBOARD -> KEYFRAME -> VIDEO -> JOINED
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow

# ---------------------------------------------------------------------------
# Constants (mirroring WorkflowConstants.java)
# ---------------------------------------------------------------------------
STAGE_STORYBOARD = "storyboard"
STAGE_KEYFRAME = "keyframe"
STAGE_VIDEO = "video"
STAGE_JOINED = "joined"

STATUS_DRAFT = "DRAFT"
STATUS_READY = "READY"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"
DEFAULT_MIN_DURATION_SECONDS = 5
DEFAULT_MAX_DURATION_SECONDS = 12

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _random_id() -> str:
    return uuid.uuid4().hex


def _trim(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = value.strip()
    return stripped if stripped else fallback.strip()


def _first_non_blank(*values: str | None) -> str:
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    s = str(value).strip().lower()
    return s in ("true", "1", "yes")


def _read_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text) or {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _write_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _default_video_size(aspect_ratio: str | None) -> str:
    return "1280*720" if _trim(aspect_ratio) == "16:9" else "720*1280"


def _normalize_duration_mode(
    duration_mode: str | None,
    min_seconds: int | None,
    max_seconds: int | None,
) -> str:
    mode = _trim(duration_mode).lower()
    if mode in ("manual", "auto"):
        return mode
    return "manual" if (min_seconds is not None or max_seconds is not None) else "auto"


def _dimensions_from_aspect_ratio(aspect_ratio: str | None) -> tuple[int, int]:
    ar = _trim(aspect_ratio)
    if ar == "16:9":
        return 1824, 1024
    if ar == "1:1":
        return 1024, 1024
    return 1024, 1824


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WorkflowService:
    """Multi-stage creative workflow service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Workflow CRUD
    # ------------------------------------------------------------------

    async def create_workflow(
        self,
        request: dict[str, Any],
        owner_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Create a draft workflow."""
        workflow_id = f"wf_{_random_id()[:12]}"
        aspect_ratio = _trim(request.get("aspectRatio", "9:16"))
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
            else max(1, _safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(_safe_int(request.get("maxDurationSeconds", min_dur)), min_dur)
        )
        now = _now_iso()
        workflow = BizStageWorkflow(
            workflow_id=workflow_id,
            owner_user_id=owner_user_id or 0,
            title=_trim(request.get("title"), "未命名工作流"),
            transcript_text=_trim(request.get("transcriptText"), ""),
            aspect_ratio=aspect_ratio,
            style_preset=_trim(request.get("stylePreset"), "cinematic"),
            text_analysis_model=_trim(request.get("textAnalysisModel"), ""),
            image_model=_trim(request.get("imageModel"), ""),
            video_model=_trim(request.get("videoModel"), ""),
            video_size=_trim(request.get("videoSize"), _default_video_size(aspect_ratio)),
            keyframe_seed=keyframe_seed,
            video_seed=video_seed,
            duration_mode=duration_mode,
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
            create_time=now,
            update_time=now,
            is_deleted=0,
        )
        self.db.add(workflow)
        await self.db.commit()
        return await self.get_workflow(workflow_id)

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
            rows.append(self._to_workflow_summary(wf, versions))
        return rows

    async def get_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Get full workflow detail with all versions and assets."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        asset_map = await self._load_asset_map(versions, wf.final_join_asset_id)
        return self._to_workflow_detail(wf, versions, asset_map)

    async def delete_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Soft delete workflow and all versions."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        asset_ids: set[str] = set()
        now = _now_iso()
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
    ) -> dict[str, Any] | None:
        """Update workflow parameters."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        aspect_ratio = _trim(request.get("aspectRatio", "9:16"))
        duration_mode = _normalize_duration_mode(
            request.get("durationMode"),
            request.get("minDurationSeconds"),
            request.get("maxDurationSeconds"),
        )
        min_dur = (
            DEFAULT_MIN_DURATION_SECONDS
            if duration_mode == "auto"
            else max(1, _safe_int(request.get("minDurationSeconds"), 1))
        )
        max_dur = (
            DEFAULT_MAX_DURATION_SECONDS
            if duration_mode == "auto"
            else max(_safe_int(request.get("maxDurationSeconds"), min_dur), min_dur)
        )
        wf.aspect_ratio = aspect_ratio
        wf.style_preset = _trim(request.get("stylePreset"), "cinematic")
        wf.text_analysis_model = _trim(request.get("textAnalysisModel"), "")
        wf.image_model = _trim(request.get("imageModel"), "")
        wf.video_model = _trim(request.get("videoModel"), "")
        wf.video_size = _trim(request.get("videoSize"), _default_video_size(aspect_ratio))
        wf.keyframe_seed = request.get("keyframeSeed")
        wf.video_seed = request.get("videoSeed")
        wf.duration_mode = duration_mode
        wf.min_duration_seconds = min_dur
        wf.max_duration_seconds = max_dur
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Storyboard
    # ------------------------------------------------------------------

    async def generate_storyboard(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Generate a storyboard version. (Stub — returns placeholder.)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "stage": STAGE_STORYBOARD,
        }

    async def select_storyboard(
        self,
        workflow_id: str,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a storyboard version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_STORYBOARD)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_STORYBOARD, 0, version_id)
        wf.selected_storyboard_version_id = version_id
        wf.current_stage = STAGE_KEYFRAME
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def adjust_storyboard(
        self,
        workflow_id: str,
        version_id: str,
        prompt: str | None = None,
    ) -> dict[str, Any] | None:
        """Adjust an existing storyboard version. (Stub)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "versionId": version_id,
            "stage": STAGE_STORYBOARD,
        }

    # ------------------------------------------------------------------
    # Keyframe
    # ------------------------------------------------------------------

    async def generate_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
    ) -> dict[str, Any] | None:
        """Generate keyframe for a clip. (Stub)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "clipIndex": clip_index,
            "stage": STAGE_KEYFRAME,
        }

    async def generate_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        frame_role: str,
    ) -> dict[str, Any] | None:
        """Generate single keyframe frame. (Stub)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "clipIndex": clip_index,
            "frameRole": frame_role,
            "stage": STAGE_KEYFRAME,
        }

    async def select_keyframe(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a keyframe version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        version = await self._require_stage_version(workflow_id, version_id, STAGE_KEYFRAME)
        if version is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_KEYFRAME, clip_index, version_id)
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def select_keyframe_frame(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
        frame_role: str,
    ) -> dict[str, Any] | None:
        """Select a keyframe frame."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        wf.current_stage = STAGE_VIDEO
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def select_character_sheet_asset(
        self,
        workflow_id: str,
        clip_index: int,
        asset_id: str,
    ) -> dict[str, Any] | None:
        """Link a character sheet material asset to a workflow clip. (Stub)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "clipIndex": clip_index,
            "assetId": asset_id,
            "stage": STAGE_KEYFRAME,
        }

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        workflow_id: str,
        clip_index: int,
    ) -> dict[str, Any] | None:
        """Generate video for a clip. (Stub)"""
        return {
            "message": "not yet implemented",
            "workflowId": workflow_id,
            "clipIndex": clip_index,
            "stage": STAGE_VIDEO,
        }

    async def select_video(
        self,
        workflow_id: str,
        clip_index: int,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Select a video version."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        await self._mark_selected_stage_version(workflow_id, STAGE_VIDEO, clip_index, version_id)
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_READY
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Finalize
    # ------------------------------------------------------------------

    async def finalize_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Concatenate videos and mark workflow as COMPLETED. (Stub — real impl needs video concat service.)"""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        wf.current_stage = STAGE_JOINED
        wf.status = STATUS_COMPLETED
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Ratings & cleanup
    # ------------------------------------------------------------------

    async def rate_workflow(
        self,
        workflow_id: str,
        rating: int,
        note: str = "",
    ) -> dict[str, Any] | None:
        """Rate a workflow (1-5)."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        wf.effect_rating = rating
        wf.effect_rating_note = note
        wf.rated_at = _now_iso()
        wf.update_time = _now_iso()
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def rate_stage_version(
        self,
        workflow_id: str,
        version_id: str,
        rating: int,
        note: str = "",
    ) -> dict[str, Any] | None:
        """Rate a stage version."""
        version = await self._require_stage_version(workflow_id, version_id, "")
        if version is None:
            return None
        version.rating = rating
        version.rating_note = note
        version.rated_at = _now_iso()
        version.update_time = _now_iso()
        if version.material_asset_id:
            asset = await self._find_asset(version.material_asset_id)
            if asset is not None:
                asset.user_rating = rating
                asset.rating_note = note
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    async def delete_stage_version(
        self,
        workflow_id: str,
        version_id: str,
    ) -> dict[str, Any] | None:
        """Delete a stage version and its downstream selections."""
        wf = await self._require_workflow(workflow_id)
        if wf is None:
            return None
        target = await self._require_stage_version(workflow_id, version_id, "")
        if target is None:
            return None
        versions = await self._list_stage_versions(workflow_id)
        to_delete = self._resolve_delete_version_chain(target, versions)
        now = _now_iso()
        for v in to_delete:
            v.selected = 0
            v.is_deleted = 1
            v.update_time = now
            if v.material_asset_id:
                await self._mark_asset_deleted(v.material_asset_id)
        wf.update_time = now
        await self.db.commit()
        return await self.get_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _require_workflow(self, workflow_id: str) -> BizStageWorkflow | None:
        stmt = select(BizStageWorkflow).where(
            BizStageWorkflow.workflow_id == workflow_id,
            BizStageWorkflow.is_deleted == 0,
        )
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
            .values(selected_for_next=0, is_deleted=1, update_time=_now_iso())
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
        now = _now_iso()
        for v in versions:
            v.selected = 1 if v.stage_version_id == selected_version_id else 0
            v.update_time = now

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

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def _to_workflow_summary(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
    ) -> dict[str, Any]:
        storyboard_count = sum(1 for v in versions if v.stage_type == STAGE_STORYBOARD)
        character_sheet_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) == VARIANT_KIND_CHARACTER_SHEET
        )
        selected_character_sheet_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) == VARIANT_KIND_CHARACTER_SHEET
            and v.selected == 1
        )
        keyframe_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
        )
        video_count = sum(1 for v in versions if v.stage_type == STAGE_VIDEO)
        selected_keyframe_count = sum(
            1
            for v in versions
            if v.stage_type == STAGE_KEYFRAME
            and _trim(_read_json(v.input_summary_json).get("variantKind", "")) != VARIANT_KIND_CHARACTER_SHEET
            and v.selected == 1
        )
        return {
            "id": wf.workflow_id,
            "title": wf.title,
            "status": wf.status,
            "currentStage": wf.current_stage,
            "aspectRatio": wf.aspect_ratio,
            "effectRating": wf.effect_rating,
            "createdAt": wf.create_time,
            "updatedAt": wf.update_time,
            "storyboardVersionCount": storyboard_count,
            "keyframeVersionCount": keyframe_count,
            "selectedKeyframeCount": selected_keyframe_count,
            "videoVersionCount": video_count,
            "characterSheetVersionCount": character_sheet_count,
            "selectedCharacterSheetCount": selected_character_sheet_count,
        }

    def _to_workflow_detail(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
        asset_map: dict[str, BizMaterialAsset],
    ) -> dict[str, Any]:
        storyboard_versions = [
            v for v in versions if v.stage_type == STAGE_STORYBOARD
        ]
        storyboard_versions.sort(key=lambda v: _safe_int(v.version_no, 0), reverse=True)
        return {
            "id": wf.workflow_id,
            "title": wf.title,
            "transcriptText": wf.transcript_text,
            "aspectRatio": wf.aspect_ratio,
            "stylePreset": wf.style_preset,
            "textAnalysisModel": wf.text_analysis_model,
            "imageModel": wf.image_model,
            "videoModel": wf.video_model,
            "videoSize": wf.video_size,
            "durationMode": wf.duration_mode or "auto",
            "minDurationSeconds": wf.min_duration_seconds,
            "maxDurationSeconds": wf.max_duration_seconds,
            "status": wf.status,
            "currentStage": wf.current_stage,
            "selectedStoryboardVersionId": wf.selected_storyboard_version_id,
            "effectRating": wf.effect_rating,
            "effectRatingNote": wf.effect_rating_note,
            "ratedAt": wf.rated_at,
            "createdAt": wf.create_time,
            "updatedAt": wf.update_time,
            "storyboardVersions": [
                self._to_stage_version_row(v, asset_map.get(v.material_asset_id))
                for v in storyboard_versions
            ],
        }

    def _to_stage_version_row(
        self,
        version: BizStageVersion,
        asset: BizMaterialAsset | None,
    ) -> dict[str, Any]:
        input_summary = _read_json(version.input_summary_json)
        output_summary = _read_json(version.output_summary_json)
        model_call_summary = _read_json(version.model_call_summary_json)
        return {
            "id": version.stage_version_id,
            "stageType": version.stage_type,
            "clipIndex": _safe_int(version.clip_index, 0),
            "versionNo": _safe_int(version.version_no, 0),
            "title": version.title,
            "status": version.status,
            "selected": version.selected == 1,
            "rating": version.rating,
            "ratingNote": version.rating_note,
            "ratedAt": version.rated_at,
            "parentVersionId": version.parent_version_id,
            "sourceMaterialAssetId": version.source_material_asset_id,
            "materialAssetId": version.material_asset_id,
            "previewUrl": version.preview_url,
            "downloadUrl": version.download_url,
            "inputSummary": input_summary,
            "outputSummary": output_summary,
            "modelCallSummary": model_call_summary,
            "createdAt": version.create_time,
            "updatedAt": version.update_time,
            "asset": self._to_material_asset_row(asset) if asset else None,
        }

    def _to_material_asset_row(
        self,
        asset: BizMaterialAsset | None,
    ) -> dict[str, Any] | None:
        if asset is None:
            return None
        metadata = _read_json(asset.metadata_json)
        return {
            "id": asset.material_asset_id,
            "workflowId": asset.workflow_id,
            "stageType": asset.stage_type,
            "mediaType": asset.media_type,
            "title": asset.title,
            "mimeType": asset.mime_type,
            "durationSeconds": asset.duration_seconds,
            "width": asset.width,
            "height": asset.height,
            "hasAudio": _safe_bool(asset.has_audio),
            "fileUrl": asset.public_url,
            "previewUrl": asset.public_url,
            "thumbnailUrl": asset.thumbnail_url or "",
            "remoteUrl": asset.remote_url,
            "userRating": asset.user_rating,
            "ratingNote": asset.rating_note,
            "originModel": asset.origin_model,
            "originProvider": asset.origin_provider,
            "metadata": metadata,
            "createdAt": asset.create_time,
            "updatedAt": asset.update_time,
        }
