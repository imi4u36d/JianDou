from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.shared import now_iso, string_value


def _optional_int(value: Any) -> int | None:
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


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _bool_to_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "on"} else 0
    return 1 if bool(value) else 0


def _metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _first_non_blank(*values: Any) -> str:
    for value in values:
        normalized = string_value(value).strip()
        if normalized:
            return normalized
    return ""


def _public_url_from_values(values: dict[str, Any]) -> str:
    return _first_non_blank(
        values.get("publicUrl"),
        values.get("fileUrl"),
        values.get("remoteUrl"),
        values.get("thirdPartyUrl"),
    )


def _thumbnail_url_from_values(values: dict[str, Any]) -> str:
    return _first_non_blank(values.get("thumbnailUrl"), values.get("previewUrl"))


def _public_url_from_row(row: BizMaterialAsset) -> str:
    return _first_non_blank(row.public_url, row.remote_url, row.third_party_url)


def _non_blank_column(column: Any) -> Any:
    return and_(column.is_not(None), column != "")


def _blank_column(column: Any) -> Any:
    return or_(column.is_(None), column == "")


def _workflow_artifact_filter() -> Any:
    return or_(
        _non_blank_column(BizMaterialAsset.workflow_id),
        BizMaterialAsset.asset_role == "workflow",
    )


def _non_workflow_artifact_filter() -> Any:
    return and_(
        _blank_column(BizMaterialAsset.workflow_id),
        or_(BizMaterialAsset.asset_role.is_(None), BizMaterialAsset.asset_role != "workflow"),
    )


class MaterialAssetService:
    """Database-backed material asset library service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_assets(
        self,
        owner_user_id: int,
        *,
        offset: int = 0,
        limit: int = 30,
        q: str | None = None,
        media_type: str | None = None,
        asset_type: str | None = None,
        min_rating: int | None = None,
        model: str | None = None,
        clip_index: int | None = None,
        include_workflow_artifacts: bool = False,
    ) -> dict[str, Any]:
        filters = [
            BizMaterialAsset.owner_user_id == owner_user_id,
            BizMaterialAsset.is_deleted == 0,
        ]
        normalized_asset_type = asset_type.strip() if asset_type and asset_type.strip() else ""
        workflow_artifacts_only = normalized_asset_type == "workflow"
        if workflow_artifacts_only:
            filters.append(_workflow_artifact_filter())
        elif not include_workflow_artifacts:
            filters.append(_non_workflow_artifact_filter())
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    BizMaterialAsset.title.ilike(pattern),
                    BizMaterialAsset.original_file_name.ilike(pattern),
                    BizMaterialAsset.origin_model.ilike(pattern),
                )
            )
        if media_type and media_type.strip():
            filters.append(BizMaterialAsset.media_type == media_type.strip())
        if normalized_asset_type and not workflow_artifacts_only:
            filters.append(BizMaterialAsset.asset_role == normalized_asset_type)
        if min_rating is not None:
            filters.append(BizMaterialAsset.user_rating >= min_rating)
        if model and model.strip():
            filters.append(BizMaterialAsset.origin_model == model.strip())
        if clip_index is not None:
            filters.append(BizMaterialAsset.clip_index == clip_index)

        total_result = await self.db.execute(select(func.count()).select_from(BizMaterialAsset).where(*filters))
        total = int(total_result.scalar_one() or 0)
        result = await self.db.execute(
            select(BizMaterialAsset)
            .where(*filters)
            .order_by(BizMaterialAsset.update_time.desc(), BizMaterialAsset.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = [self.to_view(row) for row in result.scalars().all()]
        next_offset = offset + limit if offset + limit < total else None
        return {
            "items": items,
            "offset": offset,
            "limit": limit,
            "total": total,
            "hasMore": next_offset is not None,
            "nextOffset": next_offset,
        }

    async def get_asset(self, owner_user_id: int, asset_id: str) -> dict[str, Any] | None:
        row = await self._find_owned(owner_user_id, asset_id)
        return self.to_view(row) if row else None

    async def create_asset(self, owner_user_id: int, **values: Any) -> dict[str, Any]:
        row = await self.upsert_asset(owner_user_id, **values)
        await self.db.commit()
        await self.db.refresh(row)
        return self.to_view(row)

    async def upsert_asset(self, owner_user_id: int, asset_id: str | None = None, **values: Any) -> BizMaterialAsset:
        resolved_id = string_value(asset_id) or f"mat_{uuid.uuid4().hex}"
        row = await self._find_by_asset_id(resolved_id)
        now = now_iso()
        metadata = _metadata_dict(values.get("metadata"))
        payload = {
            "remark": string_value(values.get("remark", "")),
            "owner_user_id": owner_user_id,
            "task_id": string_value(values.get("taskId", "")) or None,
            "workflow_id": string_value(values.get("workflowId", "")) or None,
            "source_task_id": string_value(values.get("sourceTaskId", "")) or None,
            "source_material_id": string_value(values.get("sourceMaterialId", "")) or None,
            "asset_role": string_value(values.get("assetType", values.get("assetRole", "free"))) or None,
            "stage_type": string_value(values.get("stageType", "material")) or None,
            "clip_index": _optional_int(values.get("clipIndex")) if "clipIndex" in values else 0,
            "version_no": _optional_int(values.get("versionNo")) if "versionNo" in values else 1,
            "selected_for_next": _bool_to_int(values.get("selectedForNext", False)),
            "user_rating": _optional_int(values.get("userRating")),
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
            "size_bytes": _optional_int(values.get("sizeBytes")),
            "sha256": string_value(values.get("sha256", "")) or None,
            "duration_seconds": _optional_float(values.get("durationSeconds")),
            "width": _optional_int(values.get("width")),
            "height": _optional_int(values.get("height")),
            "has_audio": _bool_to_int(values.get("hasAudio", False)),
            "local_storage_path": string_value(values.get("storagePath", "")) or None,
            "local_file_path": string_value(values.get("localFilePath", values.get("storagePath", ""))) or None,
            "public_url": _public_url_from_values(values) or None,
            "thumbnail_url": _thumbnail_url_from_values(values) or None,
            "third_party_url": None,
            "remote_url": None,
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
            "captured_at": string_value(values.get("capturedAt", now)) or None,
            "timezone_offset_minutes": _optional_int(values.get("timezoneOffsetMinutes")),
            "update_time": now,
            "is_deleted": 0,
        }
        if row is None:
            row = BizMaterialAsset(material_asset_id=resolved_id, create_time=now, **payload)
            self.db.add(row)
            return row
        if row.owner_user_id != owner_user_id:
            raise ValueError("material_asset_id_already_exists")
        for key, value in payload.items():
            setattr(row, key, value)
        return row

    async def rate_asset(
        self,
        owner_user_id: int,
        asset_id: str,
        *,
        rating: int,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        row = await self._find_owned(owner_user_id, asset_id)
        if row is None:
            return None
        row.user_rating = rating
        row.rating_note = note
        row.update_time = now_iso()
        await self.db.commit()
        await self.db.refresh(row)
        return self.to_view(row)

    async def rename_asset(self, owner_user_id: int, asset_id: str, *, title: str) -> dict[str, Any] | None:
        row = await self._find_owned(owner_user_id, asset_id)
        if row is None:
            return None
        row.title = title
        row.update_time = now_iso()
        await self.db.commit()
        await self.db.refresh(row)
        return self.to_view(row)

    async def mark_uploaded(self, owner_user_id: int, asset_id: str) -> dict[str, Any] | None:
        row = await self._find_owned(owner_user_id, asset_id)
        if row is None:
            return None
        row.update_time = now_iso()
        await self.db.commit()
        await self.db.refresh(row)
        return self.to_view(row)

    async def delete_asset(self, owner_user_id: int, asset_id: str) -> bool:
        row = await self._find_owned(owner_user_id, asset_id)
        if row is None:
            return False
        row.is_deleted = 1
        row.update_time = now_iso()
        await self.db.commit()
        return True

    async def _find_by_asset_id(self, asset_id: str) -> BizMaterialAsset | None:
        result = await self.db.execute(
            select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == asset_id)
        )
        return result.scalar_one_or_none()

    async def _find_owned(self, owner_user_id: int, asset_id: str) -> BizMaterialAsset | None:
        result = await self.db.execute(
            select(BizMaterialAsset).where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.owner_user_id == owner_user_id,
                BizMaterialAsset.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def to_view(row: BizMaterialAsset) -> dict[str, Any]:
        metadata = _metadata_dict(row.metadata_json)
        public_url = _public_url_from_row(row)
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
            "metadata": metadata,
            "createdAt": row.create_time or row.captured_at or "",
            "updatedAt": row.update_time or row.create_time or "",
            "status": "ready" if not row.is_deleted else "deleted",
        }
