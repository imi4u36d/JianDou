from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from backend.domain.enums import WorkflowStage
from backend.models.task import BizMaterialAsset
from backend.models.workflow import BizStageVersion, BizStageWorkflow

STAGE_STORYBOARD = WorkflowStage.STORYBOARD.value
STAGE_KEYFRAME = WorkflowStage.KEYFRAME.value
STAGE_VIDEO = WorkflowStage.VIDEO.value
CHARACTER_SHEET_CLIP_INDEX_BASE = 1000
VARIANT_KIND_CHARACTER_SHEET = "character_sheet"

StoryboardPlanResolver = Callable[[BizStageVersion | None], tuple[list[dict[str, Any]], list[dict[str, Any]]]]


def _trim(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = value.strip()
    return stripped if stripped else fallback.strip()


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


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in ("true", "1", "yes")


def _read_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


class WorkflowViewMapper:
    """Build API-facing workflow response dictionaries from ORM rows."""

    def __init__(self, storyboard_plan_resolver: StoryboardPlanResolver) -> None:
        self._storyboard_plan = storyboard_plan_resolver

    def to_workflow_summary(
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
            "characterSheetCount": character_sheet_count,
            "selectedCharacterSheetCount": selected_character_sheet_count,
            "executionMode": wf.execution_mode,
            "autoPilotState": wf.auto_pilot_state,
        }

    def to_workflow_detail(
        self,
        wf: BizStageWorkflow,
        versions: list[BizStageVersion],
        asset_map: dict[str, BizMaterialAsset],
    ) -> dict[str, Any]:
        storyboard_versions = [v for v in versions if v.stage_type == STAGE_STORYBOARD]
        storyboard_versions.sort(key=lambda v: _safe_int(v.version_no, 0), reverse=True)
        selected_storyboard = next(
            (v for v in storyboard_versions if v.stage_version_id == wf.selected_storyboard_version_id),
            None,
        )
        if selected_storyboard is None:
            selected_storyboard = next((v for v in storyboard_versions if v.selected == 1), None)
        if selected_storyboard is None and storyboard_versions:
            selected_storyboard = storyboard_versions[0]
        characters, storyboard_clips = self._storyboard_plan(selected_storyboard)

        keyframe_versions = [v for v in versions if v.stage_type == STAGE_KEYFRAME]
        video_versions = [v for v in versions if v.stage_type == STAGE_VIDEO]

        keyframe_by_clip: dict[int, list[BizStageVersion]] = {}
        for version in keyframe_versions:
            clip_idx = _safe_int(version.clip_index, 0)
            keyframe_by_clip.setdefault(clip_idx, []).append(version)

        video_by_clip: dict[int, list[BizStageVersion]] = {}
        for version in video_versions:
            clip_idx = _safe_int(version.clip_index, 0)
            video_by_clip.setdefault(clip_idx, []).append(version)

        storyboard_clip_indexes = [_safe_int(item.get("clipIndex"), 0) for item in storyboard_clips]
        all_clip_indexes = sorted(
            idx for idx in set(storyboard_clip_indexes + list(keyframe_by_clip) + list(video_by_clip))
            if 0 < idx < CHARACTER_SHEET_CLIP_INDEX_BASE
        )

        clip_slots = []
        for clip_idx in all_clip_indexes:
            clip = next((item for item in storyboard_clips if _safe_int(item.get("clipIndex"), 0) == clip_idx), {})
            clip_slots.append({
                "clipIndex": clip_idx,
                "shotLabel": clip.get("shotLabel") or f"镜头 {clip_idx:03d}",
                "scene": clip.get("scene"),
                "durationHint": clip.get("durationHint"),
                "targetDurationSeconds": clip.get("targetDurationSeconds"),
                "matchedCharacters": None,
                "keyframeVersions": [
                    self.to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sorted(keyframe_by_clip.get(clip_idx, []), key=lambda v: _safe_int(v.version_no, 0), reverse=True)
                ],
                "videoVersions": [
                    self.to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sorted(video_by_clip.get(clip_idx, []), key=lambda v: _safe_int(v.version_no, 0), reverse=True)
                ],
            })

        character_sheets = []
        for idx, character in enumerate(characters, start=1):
            synthetic_clip_index = CHARACTER_SHEET_CLIP_INDEX_BASE + idx
            sheet_versions = sorted(
                keyframe_by_clip.get(synthetic_clip_index, []),
                key=lambda v: _safe_int(v.version_no, 0),
                reverse=True,
            )
            character_sheets.append({
                "id": f"{wf.workflow_id}-character-{idx}",
                "characterName": character.get("name", ""),
                "name": character.get("name", ""),
                "displayName": character.get("name", ""),
                "appearanceSummary": character.get("summary", ""),
                "appearance": character.get("appearance", ""),
                "syntheticClipIndex": synthetic_clip_index,
                "clipIndex": synthetic_clip_index,
                "versions": [
                    self.to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sheet_versions
                ],
                "keyframeVersions": [
                    self.to_stage_version_row(v, asset_map.get(v.material_asset_id))
                    for v in sheet_versions
                ],
            })

        return {
            "id": wf.workflow_id,
            "title": wf.title,
            "transcriptText": wf.transcript_text,
            "aspectRatio": wf.aspect_ratio,
            "textAnalysisModel": wf.text_analysis_model,
            "imageModel": wf.image_model,
            "videoModel": wf.video_model,
            "videoSize": wf.video_size,
            "keyframeSeed": wf.keyframe_seed,
            "videoSeed": wf.video_seed,
            "seed": None,
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
            "executionMode": wf.execution_mode,
            "autoPilotState": wf.auto_pilot_state,
            "autoPilotNextStage": wf.auto_pilot_next_stage,
            "autoPilotErrorMessage": wf.auto_pilot_error_message,
            "autoPilotStartedAt": wf.auto_pilot_started_at,
            "autoPilotPausedAt": wf.auto_pilot_paused_at,
            "autoPilotCurrentTask": wf.auto_pilot_current_task,
            "storyboardVersions": [
                self.to_stage_version_row(v, asset_map.get(v.material_asset_id))
                for v in storyboard_versions
            ],
            "characterSheets": character_sheets,
            "clipSlots": clip_slots,
            "finalResult": self.to_material_asset_row(asset_map.get(wf.final_join_asset_id)) if wf.final_join_asset_id else None,
        }

    def to_stage_version_row(
        self,
        version: BizStageVersion,
        asset: BizMaterialAsset | None,
    ) -> dict[str, Any]:
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
            "inputSummary": _read_json(version.input_summary_json),
            "outputSummary": _read_json(version.output_summary_json),
            "modelCallSummary": _read_json(version.model_call_summary_json),
            "createdAt": version.create_time,
            "updatedAt": version.update_time,
            "asset": self.to_material_asset_row(asset) if asset else None,
        }

    @staticmethod
    def to_material_asset_row(asset: BizMaterialAsset | None) -> dict[str, Any] | None:
        if asset is None:
            return None
        public_url = _trim(asset.public_url) or _trim(asset.remote_url) or _trim(asset.third_party_url)
        thumbnail_url = _trim(asset.thumbnail_url)
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
            "publicUrl": public_url,
            "fileUrl": public_url,
            "previewUrl": thumbnail_url,
            "thumbnailUrl": thumbnail_url,
            "remoteUrl": "",
            "userRating": asset.user_rating,
            "ratingNote": asset.rating_note,
            "originModel": asset.origin_model,
            "originProvider": asset.origin_provider,
            "metadata": _read_json(asset.metadata_json),
            "createdAt": asset.create_time,
            "updatedAt": asset.update_time,
        }
