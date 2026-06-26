from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.errors import bad_request, not_found
from backend.schemas.public_share import CreatePublicShareRequest, PublicShareDeleteResult
from backend.services.public_share_service import PublicShareService

router = APIRouter(prefix="/api/v3/public-shares", tags=["public-shares"])


def _service(db: AsyncSession) -> PublicShareService:
    return PublicShareService(db)


@router.get("")
async def list_public_shares(
    request: Request,
    db: AsyncSession = Depends(get_db),
    type: str | None = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("popular"),
):
    user = await require_user(request)
    return await _service(db).list_shares(user["id"], media_type=type, offset=offset, limit=limit, sort=sort)


@router.post("")
async def create_public_share(
    payload: CreatePublicShareRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    try:
        return await _service(db).create_share(
            user["id"],
            material_asset_id=payload.material_asset_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
        )
    except ValueError as exc:
        raise bad_request(str(exc))


@router.delete("/{share_id}", response_model=PublicShareDeleteResult)
async def delete_public_share(
    share_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    deleted = await _service(db).remove_share(user["id"], share_id)
    if not deleted:
        raise not_found("public_share")
    return PublicShareDeleteResult(deleted=True, share_id=share_id)


@router.post("/{share_id}/like")
async def like_public_share(
    share_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    share = await _service(db).like_share(user["id"], share_id)
    if share is None:
        raise not_found("public_share")
    return share


@router.delete("/{share_id}/like")
async def unlike_public_share(
    share_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    share = await _service(db).unlike_share(user["id"], share_id)
    if share is None:
        raise not_found("public_share")
    return share
