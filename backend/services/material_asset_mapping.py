"""Input normalization and response projection for material assets."""

from __future__ import annotations

import json
from typing import Any

from backend.models.task import BizMaterialAsset
from backend.shared import string_value


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def bool_to_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "on"} else 0
    return 1 if bool(value) else 0


def metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def first_non_blank(*values: Any) -> str:
    for value in values:
        normalized = string_value(value).strip()
        if normalized:
            return normalized
    return ""


def material_asset_payload(
    owner_user_id: int,
    values: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    metadata = metadata_dict(values.get("metadata"))
    storage_path = string_value(values.get("storagePath", "")) or None
    return {
        "remark": string_value(values.get("remark", "")),
        "owner_user_id": owner_user_id,
        "task_id": string_value(values.get("taskId", "")) or None,
        "workflow_id": string_value(values.get("workflowId", "")) or None,
        "source_task_id": string_value(values.get("sourceTaskId", "")) or None,
        "source_material_id": string_value(values.get("sourceMaterialId", "")) or None,
        "asset_role": string_value(values.get("assetType", values.get("assetRole", "free"))) or None,
        "stage_type": string_value(values.get("stageType", "material")) or None,
        "clip_index": optional_int(values.get("clipIndex")) if "clipIndex" in values else 0,
        "version_no": optional_int(values.get("versionNo")) if "versionNo" in values else 1,
        "selected_for_next": bool_to_int(values.get("selectedForNext", False)),
        "user_rating": optional_int(values.get("userRating")),
        "rating_note": string_value(values.get("ratingNote", "")) or None,
        "media_type": string_value(values.get("mediaType", "image")) or None,
        "title": string_value(values.get("title", "素材")) or None,
        "origin_provider": string_value(values.get("originProvider", "")) or None,
        "origin_model": string_value(values.get("originModel", "")) or None,
        "remote_task_id": string_value(values.get("remoteTaskId", "")) or None,
        "remote_asset_id": string_value(values.get("remoteAssetId", "")) or None,
        "original_file_name": string_value(values.get("originalFileName", "")) or None,
        "stored_file_name": string_value(values.get("storedFileName", "")) or None,
        "file_ext": string_value(values.get("fileExt", "")) or None,
        "storage_provider": string_value(values.get("storageProvider", "")) or None,
        "mime_type": string_value(values.get("mimeType", "")) or None,
        "size_bytes": optional_int(values.get("sizeBytes")),
        "sha256": string_value(values.get("sha256", "")) or None,
        "duration_seconds": optional_float(values.get("durationSeconds")),
        "width": optional_int(values.get("width")),
        "height": optional_int(values.get("height")),
        "has_audio": bool_to_int(values.get("hasAudio", False)),
        "local_storage_path": storage_path,
        "local_file_path": string_value(values.get("localFilePath", storage_path or "")) or None,
        "public_url": first_non_blank(
            values.get("publicUrl"),
            values.get("fileUrl"),
            values.get("remoteUrl"),
            values.get("thirdPartyUrl"),
        ) or None,
        "thumbnail_url": first_non_blank(
            values.get("thumbnailUrl"), values.get("previewUrl")
        ) or None,
        "third_party_url": None,
        "remote_url": None,
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
        "captured_at": string_value(values.get("capturedAt", timestamp)) or None,
        "timezone_offset_minutes": optional_int(values.get("timezoneOffsetMinutes")),
        "update_time": timestamp,
        "is_deleted": 0,
    }


def material_asset_view(row: BizMaterialAsset) -> dict[str, Any]:
    public_url = first_non_blank(row.public_url, row.remote_url, row.third_party_url)
    thumbnail_url = row.thumbnail_url or ""
    return {
        "id": row.material_asset_id,
        "materialAssetId": row.material_asset_id,
        "workflowId": row.workflow_id,
        "taskId": row.task_id or "",
        "stageType": row.stage_type or "material",
        "clipIndex": row.clip_index if row.clip_index is not None else 0,
        "versionNo": row.version_no if row.version_no is not None else 1,
        "selectedForNext": bool(row.selected_for_next),
        "assetType": row.asset_role or "free",
        "assetRole": row.asset_role,
        "userRating": row.user_rating,
        "ratingNote": row.rating_note,
        "mediaType": row.media_type or "image",
        "title": row.title or "素材",
        "originModel": row.origin_model,
        "originProvider": row.origin_provider,
        "mimeType": row.mime_type,
        "durationSeconds": row.duration_seconds,
        "width": row.width,
        "height": row.height,
        "hasAudio": bool(row.has_audio),
        "publicUrl": public_url,
        "fileUrl": public_url,
        "previewUrl": thumbnail_url,
        "thumbnailUrl": thumbnail_url,
        "remoteUrl": "",
        "hasRemotePath": False,
        "remotePath": "",
        "metadata": metadata_dict(row.metadata_json),
        "createdAt": row.create_time or row.captured_at or "",
        "updatedAt": row.update_time or row.create_time or "",
        "status": "ready" if not row.is_deleted else "deleted",
    }
