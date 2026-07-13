from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import BizMaterialAsset
from backend.services.material_asset_mapping import material_asset_payload, material_asset_view
from backend.shared import now_iso, string_value


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
        payload = material_asset_payload(owner_user_id, values, now)
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

    to_view = staticmethod(material_asset_view)
