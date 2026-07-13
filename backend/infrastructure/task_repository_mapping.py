"""Pure mapping helpers for task repository persistence and lightweight responses."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import StageRunStatus
from backend.domain.json_payloads import read_json_object, write_json_object
from backend.domain.task_record import TaskRecord
from backend.models.task import BizMaterialAsset, BizTask
from backend.shared import safe_int, string_value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def _stage_run_status(value: Any) -> str:
    status = StageRunStatus._missing_(string_value(value))
    return status.value if status is not None else StageRunStatus.FAILED.value


def _first_non_blank(*values: Any) -> str:
    for value in values:
        normalized = string_value(value).strip()
        if normalized:
            return normalized
    return ""


def _material_public_url_from_row(row: BizMaterialAsset) -> str:
    return _first_non_blank(row.public_url, row.remote_url, row.third_party_url)


def _material_public_url_from_payload(row: dict[str, Any]) -> str:
    return _light_url(
        _first_non_blank(row.get("publicUrl"), row.get("fileUrl"), row.get("remoteUrl"), row.get("thirdPartyUrl")), 1024
    )


def _material_thumbnail_url_from_payload(row: dict[str, Any]) -> str:
    return _light_url(_first_non_blank(row.get("thumbnailUrl"), row.get("previewUrl")), 1024)


def _looks_like_image_url(value: Any) -> bool:
    url = string_value(value).lower()
    return url.startswith("/storage/thumbs/") or url.endswith((".avif", ".gif", ".jpg", ".jpeg", ".png", ".webp"))


def _short_text(value: Any, limit: int = 2000) -> str:
    return string_value(value)[:limit]


def _light_url(value: Any, max_length: int = 2048) -> str:
    url = string_value(value)
    if not url or len(url) > max_length:
        return ""
    lowered = url.lower()
    if lowered.startswith(("data:", "blob:")) or ";base64" in lowered:
        return ""
    return url


def _light_request_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    passthrough_keys = (
        "taskType",
        "assetType",
        "aspectRatio",
        "imageSize",
        "textAnalysisModel",
        "imageModel",
        "videoModel",
        "videoSize",
        "seed",
        "videoDurationSeconds",
        "outputCount",
        "minDurationSeconds",
        "maxDurationSeconds",
        "stopBeforeVideoGeneration",
        "referenceAssetIds",
    )
    result = {key: payload[key] for key in passthrough_keys if key in payload}
    if "title" in payload:
        result["title"] = _short_text(payload.get("title"), 200)
    if "creativePrompt" in payload:
        result["creativePrompt"] = _short_text(payload.get("creativePrompt"))
    transcript_text = string_value(payload.get("transcriptText"))
    if transcript_text:
        result["transcriptText"] = transcript_text[:2000]
    reference_urls = payload.get("referenceImageUrls")
    if isinstance(reference_urls, list):
        result["referenceImageUrls"] = [url for url in (_light_url(item) for item in reference_urls[:12]) if url]
    return result


# ---------------------------------------------------------------------------
# Mapping helpers: TaskRecord <-> BizTask
# ---------------------------------------------------------------------------


def _biz_task_from_record(record: TaskRecord) -> BizTask:
    """Convert a TaskRecord into a BizTask ORM instance."""
    return BizTask(
        task_id=record.id,
        owner_user_id=record.owner_user_id or 0,
        task_type=record.task_type or "video_generation",
        title=record.title or "",
        description=None,
        aspect_ratio=record.aspect_ratio or "",
        min_duration_seconds=record.min_duration_seconds or 0,
        max_duration_seconds=record.max_duration_seconds or 0,
        output_count=record.completed_output_count or 0,
        source_primary_asset_id="",
        source_file_name=record.source_file_name or "",
        source_asset_ids_json=None,
        source_file_names_json=None,
        request_payload_json=write_json_object(record.request_snapshot) if record.request_snapshot else None,
        context_json=write_json_object(record.execution_context) if record.execution_context else None,
        intro_template=record.intro_template or "",
        outro_template=record.outro_template or "",
        creative_prompt=record.creative_prompt,
        task_seed=record.task_seed,
        effect_rating=record.effect_rating,
        effect_rating_note=record.effect_rating_note or "",
        rated_at=record.rated_at,
        model_provider="",
        execution_mode="",
        editing_mode=record.editing_mode or "",
        status=record.status or "",
        progress=record.progress or 0,
        error_code="",
        error_message=record.error_message,
        plan_json=None,
        retry_count=record.retry_count or 0,
        timezone_offset_minutes=0,
        started_at=record.started_at,
        finished_at=record.finished_at,
        create_time=record.created_at or "",
        update_time=record.updated_at or "",
        is_deleted=0,
        remark="",
    )


def _material_from_row(row: BizMaterialAsset) -> dict[str, Any]:
    metadata = read_json_object(row.metadata_json)
    public_url = _material_public_url_from_row(row)
    thumbnail_url = row.thumbnail_url or ""
    return {
        "id": row.material_asset_id,
        "materialAssetId": row.material_asset_id,
        "ownerUserId": row.owner_user_id,
        "taskId": row.task_id or "",
        "workflowId": row.workflow_id or "",
        "sourceTaskId": row.source_task_id or "",
        "sourceMaterialId": row.source_material_id or "",
        "kind": row.asset_role or "",
        "assetRole": row.asset_role or "",
        "stageType": row.stage_type or "",
        "clipIndex": row.clip_index or 0,
        "versionNo": row.version_no,
        "selectedForNext": row.selected_for_next or 0,
        "userRating": row.user_rating,
        "ratingNote": row.rating_note or "",
        "mediaType": row.media_type or "",
        "title": row.title or "",
        "originProvider": row.origin_provider or "",
        "originModel": row.origin_model or "",
        "remoteTaskId": row.remote_task_id or "",
        "remoteAssetId": row.remote_asset_id or "",
        "originalFileName": row.original_file_name or "",
        "storedFileName": row.stored_file_name or "",
        "fileExt": row.file_ext or "",
        "storageProvider": row.storage_provider or "",
        "mimeType": row.mime_type or "",
        "sizeBytes": row.size_bytes or 0,
        "sha256": row.sha256 or "",
        "durationSeconds": row.duration_seconds or 0,
        "width": row.width or 0,
        "height": row.height or 0,
        "hasAudio": bool(row.has_audio),
        "storagePath": row.local_storage_path or "",
        "localFilePath": row.local_file_path or "",
        "publicUrl": public_url,
        "fileUrl": public_url,
        "previewUrl": thumbnail_url,
        "thumbnailUrl": thumbnail_url,
        "thirdPartyUrl": "",
        "remoteUrl": "",
        "metadata": metadata,
        "createdAt": row.captured_at or row.create_time or "",
    }


def _material_from_row_without_metadata(row: BizMaterialAsset) -> dict[str, Any]:
    public_url = _light_url(_material_public_url_from_row(row))
    thumbnail_url = _light_url(row.thumbnail_url)
    return {
        "id": row.material_asset_id,
        "materialAssetId": row.material_asset_id,
        "ownerUserId": row.owner_user_id,
        "taskId": row.task_id or "",
        "workflowId": row.workflow_id or "",
        "sourceTaskId": row.source_task_id or "",
        "sourceMaterialId": row.source_material_id or "",
        "kind": row.asset_role or "",
        "assetRole": row.asset_role or "",
        "stageType": row.stage_type or "",
        "clipIndex": row.clip_index or 0,
        "versionNo": row.version_no,
        "selectedForNext": row.selected_for_next or 0,
        "userRating": row.user_rating,
        "ratingNote": row.rating_note or "",
        "mediaType": row.media_type or "",
        "title": row.title or "",
        "originProvider": row.origin_provider or "",
        "originModel": row.origin_model or "",
        "remoteTaskId": row.remote_task_id or "",
        "remoteAssetId": row.remote_asset_id or "",
        "originalFileName": row.original_file_name or "",
        "storedFileName": row.stored_file_name or "",
        "fileExt": row.file_ext or "",
        "storageProvider": row.storage_provider or "",
        "mimeType": row.mime_type or "",
        "sizeBytes": row.size_bytes or 0,
        "sha256": row.sha256 or "",
        "durationSeconds": row.duration_seconds or 0,
        "width": row.width or 0,
        "height": row.height or 0,
        "hasAudio": bool(row.has_audio),
        "storagePath": "",
        "localFilePath": "",
        "publicUrl": public_url,
        "fileUrl": public_url,
        "previewUrl": thumbnail_url,
        "thumbnailUrl": thumbnail_url,
        "thirdPartyUrl": "",
        "remoteUrl": "",
        "metadata": {},
        "createdAt": row.captured_at or row.create_time or "",
    }


def _record_from_biz_task(row: BizTask) -> TaskRecord:
    """Convert a BizTask ORM row into a TaskRecord."""
    request_snapshot = read_json_object(row.request_payload_json)
    execution_context = read_json_object(row.context_json)

    rec = TaskRecord(
        id=row.task_id or "",
        owner_user_id=row.owner_user_id,
        task_type=row.task_type or "video_generation",
        title=row.title or "",
        aspect_ratio=row.aspect_ratio or "",
        min_duration_seconds=row.min_duration_seconds or 8,
        max_duration_seconds=row.max_duration_seconds or 8,
        retry_count=row.retry_count or 0,
        started_at=row.started_at,
        finished_at=row.finished_at,
        completed_output_count=safe_int(execution_context.get("completedOutputCount"), 0),
        current_attempt_no=0,
        has_transcript=bool(string_value(request_snapshot.get("transcriptText"))),
        has_timed_transcript=False,
        source_asset_count=0,
        editing_mode=row.editing_mode or "",
        is_queued=False,
        queue_position=None,
        active_attempt_id="",
        intro_template=row.intro_template or "",
        outro_template=row.outro_template or "",
        creative_prompt=row.creative_prompt or "",
        task_seed=row.task_seed,
        effect_rating=row.effect_rating,
        effect_rating_note=row.effect_rating_note or "",
        rated_at=row.rated_at,
        error_message=row.error_message or "",
        transcript_text=string_value(request_snapshot.get("transcriptText")),
        storyboard_script=string_value(execution_context.get("analysisScriptText")),
        status=row.status or "",
        progress=row.progress or 0,
        created_at=row.create_time or "",
        updated_at=row.update_time or "",
        source_file_name=row.source_file_name or "",
        execution_context=execution_context,
        request_snapshot=request_snapshot,
    )
    return rec


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


# =============================================================================
# TASK REPOSITORY
# =============================================================================
