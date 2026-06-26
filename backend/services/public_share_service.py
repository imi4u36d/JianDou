from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.public_share import BizPublicShare, BizPublicShareLike
from backend.models.task import BizMaterialAsset
from backend.models.user import SysUser
from backend.shared import now_iso, string_value

ACTIVE = "ACTIVE"
REMOVED = "REMOVED"


def _normalize_media_type(value: Any, mime_type: Any = "") -> str:
    raw = string_value(value).strip().lower()
    mime = string_value(mime_type).strip().lower()
    if "video" in raw or mime.startswith("video/"):
        return "video"
    if "image" in raw or mime.startswith("image/"):
        return "image"
    return raw


def _public_url(asset: BizMaterialAsset) -> str:
    return string_value(asset.public_url or asset.remote_url or asset.third_party_url)


def _thumbnail_url(asset: BizMaterialAsset) -> str:
    return string_value(asset.thumbnail_url)


class PublicShareService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_shares(
        self,
        user_id: int,
        *,
        media_type: str | None = None,
        offset: int = 0,
        limit: int = 30,
        sort: str = "popular",
    ) -> dict[str, Any]:
        filters = [BizPublicShare.status == ACTIVE, BizPublicShare.is_deleted == 0]
        normalized_type = _normalize_media_type(media_type)
        if normalized_type in {"image", "video"}:
            filters.append(BizPublicShare.media_type == normalized_type)

        total_result = await self.db.execute(
            select(func.count())
            .select_from(BizPublicShare)
            .join(BizMaterialAsset, BizMaterialAsset.material_asset_id == BizPublicShare.material_asset_id)
            .where(*filters, BizMaterialAsset.is_deleted == 0)
        )
        total = int(total_result.scalar_one() or 0)

        order_by = (
            [BizPublicShare.like_count.desc(), BizPublicShare.create_time.desc(), BizPublicShare.id.desc()]
            if sort != "latest"
            else [BizPublicShare.create_time.desc(), BizPublicShare.id.desc()]
        )
        result = await self.db.execute(
            select(BizPublicShare, BizMaterialAsset, SysUser)
            .join(BizMaterialAsset, BizMaterialAsset.material_asset_id == BizPublicShare.material_asset_id)
            .join(SysUser, SysUser.id == BizPublicShare.owner_user_id)
            .where(*filters, BizMaterialAsset.is_deleted == 0)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()
        share_ids = [row[0].share_id for row in rows]
        liked_ids = await self._liked_share_ids(user_id, share_ids)
        items = [self.to_view(share, asset, user, share.share_id in liked_ids) for share, asset, user in rows]
        next_offset = offset + limit if offset + limit < total else None
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
            "hasMore": next_offset is not None,
            "nextOffset": next_offset,
        }

    async def create_share(
        self,
        user_id: int,
        *,
        material_asset_id: str,
        source_type: str,
        source_id: str,
    ) -> dict[str, Any]:
        asset = await self._find_owned_asset(user_id, material_asset_id)
        if asset is None:
            raise ValueError("material_asset_not_found")
        media_type = _normalize_media_type(asset.media_type, asset.mime_type)
        if media_type not in {"image", "video"}:
            raise ValueError("unsupported_share_media_type")
        if not _public_url(asset):
            raise ValueError("share_media_url_required")

        normalized_source_type = string_value(source_type).strip().lower() or "task"
        if normalized_source_type not in {"task", "workflow", "material"}:
            raise ValueError("unsupported_share_source_type")
        resolved_source_id = string_value(source_id).strip()
        if not resolved_source_id:
            resolved_source_id = string_value(
                asset.workflow_id
                if normalized_source_type == "workflow"
                else asset.material_asset_id
                if normalized_source_type == "material"
                else asset.task_id
            )
        self._validate_source(asset, normalized_source_type, resolved_source_id)

        row = await self._find_share_by_material(asset.material_asset_id)
        now = now_iso()
        if row is None:
            row = BizPublicShare(
                share_id=f"share_{uuid.uuid4().hex}",
                owner_user_id=user_id,
                material_asset_id=asset.material_asset_id,
                source_type=normalized_source_type,
                source_id=resolved_source_id,
                media_type=media_type,
                title=asset.title or "生成结果",
                status=ACTIVE,
                like_count=0,
                create_time=now,
                update_time=now,
                is_deleted=0,
                remark="",
            )
            self.db.add(row)
        elif row.owner_user_id != user_id:
            raise ValueError("material_already_shared")
        else:
            row.source_type = normalized_source_type
            row.source_id = resolved_source_id
            row.media_type = media_type
            row.title = asset.title or row.title or "生成结果"
            row.status = ACTIVE
            row.is_deleted = 0
            row.update_time = now

        await self.db.commit()
        await self.db.refresh(row)
        owner = await self._find_user(user_id)
        liked_ids = await self._liked_share_ids(user_id, [row.share_id])
        return self.to_view(row, asset, owner, row.share_id in liked_ids)

    async def remove_share(self, user_id: int, share_id: str) -> bool:
        row = await self._find_share(share_id)
        if row is None or row.owner_user_id != user_id or row.is_deleted != 0:
            return False
        row.status = REMOVED
        row.update_time = now_iso()
        await self.db.commit()
        return True

    async def like_share(self, user_id: int, share_id: str) -> dict[str, Any] | None:
        row = await self._find_active_share(share_id)
        if row is None:
            return None
        like = await self._find_like(share_id, user_id)
        now = now_iso()
        if like is None:
            like = BizPublicShareLike(
                like_id=f"like_{uuid.uuid4().hex}",
                share_id=share_id,
                user_id=user_id,
                create_time=now,
                update_time=now,
                is_deleted=0,
                remark="",
            )
            self.db.add(like)
            row.like_count = int(row.like_count or 0) + 1
        elif like.is_deleted:
            like.is_deleted = 0
            like.update_time = now
            row.like_count = int(row.like_count or 0) + 1
        await self.db.commit()
        return await self.get_share(user_id, share_id)

    async def unlike_share(self, user_id: int, share_id: str) -> dict[str, Any] | None:
        row = await self._find_active_share(share_id)
        if row is None:
            return None
        like = await self._find_like(share_id, user_id)
        if like is not None and like.is_deleted == 0:
            like.is_deleted = 1
            like.update_time = now_iso()
            row.like_count = max(0, int(row.like_count or 0) - 1)
            await self.db.commit()
        return await self.get_share(user_id, share_id)

    async def get_share(self, user_id: int, share_id: str) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(BizPublicShare, BizMaterialAsset, SysUser)
            .join(BizMaterialAsset, BizMaterialAsset.material_asset_id == BizPublicShare.material_asset_id)
            .join(SysUser, SysUser.id == BizPublicShare.owner_user_id)
            .where(
                BizPublicShare.share_id == share_id,
                BizPublicShare.status == ACTIVE,
                BizPublicShare.is_deleted == 0,
                BizMaterialAsset.is_deleted == 0,
            )
        )
        row = result.first()
        if row is None:
            return None
        liked_ids = await self._liked_share_ids(user_id, [share_id])
        return self.to_view(row[0], row[1], row[2], share_id in liked_ids)

    async def _find_owned_asset(self, user_id: int, asset_id: str) -> BizMaterialAsset | None:
        result = await self.db.execute(
            select(BizMaterialAsset).where(
                BizMaterialAsset.material_asset_id == asset_id,
                BizMaterialAsset.owner_user_id == user_id,
                BizMaterialAsset.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def _find_share_by_material(self, asset_id: str) -> BizPublicShare | None:
        result = await self.db.execute(select(BizPublicShare).where(BizPublicShare.material_asset_id == asset_id))
        return result.scalar_one_or_none()

    async def _find_share(self, share_id: str) -> BizPublicShare | None:
        result = await self.db.execute(select(BizPublicShare).where(BizPublicShare.share_id == share_id))
        return result.scalar_one_or_none()

    async def _find_active_share(self, share_id: str) -> BizPublicShare | None:
        result = await self.db.execute(
            select(BizPublicShare).where(
                BizPublicShare.share_id == share_id,
                BizPublicShare.status == ACTIVE,
                BizPublicShare.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def _find_like(self, share_id: str, user_id: int) -> BizPublicShareLike | None:
        result = await self.db.execute(
            select(BizPublicShareLike).where(BizPublicShareLike.share_id == share_id, BizPublicShareLike.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _liked_share_ids(self, user_id: int, share_ids: list[str]) -> set[str]:
        if not share_ids:
            return set()
        result = await self.db.execute(
            select(BizPublicShareLike.share_id).where(
                BizPublicShareLike.share_id.in_(share_ids),
                BizPublicShareLike.user_id == user_id,
                BizPublicShareLike.is_deleted == 0,
            )
        )
        return {string_value(value) for value in result.scalars().all()}

    async def _find_user(self, user_id: int) -> SysUser:
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("user_not_found")
        return user

    @staticmethod
    def _validate_source(asset: BizMaterialAsset, source_type: str, source_id: str) -> None:
        if not source_id:
            raise ValueError("share_source_id_required")
        if source_type == "workflow":
            if string_value(asset.workflow_id) != source_id:
                raise ValueError("share_source_mismatch")
            return
        if source_type == "material":
            if string_value(asset.material_asset_id) != source_id:
                raise ValueError("share_source_mismatch")
            return
        if source_type == "task" and string_value(asset.task_id) != source_id:
            raise ValueError("share_source_mismatch")

    @staticmethod
    def to_view(
        share: BizPublicShare,
        asset: BizMaterialAsset,
        owner: SysUser,
        liked_by_me: bool,
    ) -> dict[str, Any]:
        return {
            "id": share.share_id,
            "shareId": share.share_id,
            "materialAssetId": share.material_asset_id,
            "sourceType": share.source_type,
            "sourceId": share.source_id,
            "ownerUserId": share.owner_user_id,
            "authorName": owner.username,
            "title": share.title or asset.title or "生成结果",
            "mediaType": share.media_type,
            "publicUrl": _public_url(asset),
            "fileUrl": _public_url(asset),
            "previewUrl": _thumbnail_url(asset),
            "thumbnailUrl": _thumbnail_url(asset),
            "width": asset.width,
            "height": asset.height,
            "durationSeconds": asset.duration_seconds,
            "likeCount": int(share.like_count or 0),
            "likedByMe": liked_by_me,
            "sharedAt": share.create_time,
            "updatedAt": share.update_time,
            "status": share.status,
        }
