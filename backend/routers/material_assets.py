from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.schemas.material import RateMaterialAssetRequest
from backend.services.material_asset_service import MaterialAssetService
from backend.services.workflow_service import WorkflowService

router = APIRouter(prefix="/api/v3/material-assets", tags=["material-assets"])


def _service(db: AsyncSession) -> MaterialAssetService:
    return MaterialAssetService(db)


@router.get("")
async def list_material_assets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None),
    type: str | None = Query(default=None),
    assetType: str | None = Query(default=None),
    minRating: int | None = Query(default=None, ge=1, le=5),
    model: str | None = Query(default=None),
    clipIndex: int | None = Query(default=None, ge=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=200),
):
    user = await require_user(request)
    return await _service(db).list_assets(
        user["id"],
        offset=offset,
        limit=limit,
        q=q,
        media_type=type,
        asset_type=assetType,
        min_rating=minRating,
        model=model,
        clip_index=clipIndex,
    )


@router.post("")
async def create_material_asset(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    return await _service(db).create_asset(user["id"], title="素材", mediaType="text", assetType="free")


@router.get("/{asset_id}")
async def get_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    asset = await _service(db).get_asset(user["id"], asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="material_asset_not_found")
    return asset


@router.delete("/{asset_id}")
async def delete_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    deleted = await _service(db).delete_asset(user["id"], asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="material_asset_not_found")
    return {"deleted": True, "assetId": asset_id}


@router.patch("/{asset_id}/rating")
async def rate_material_asset(
    asset_id: str,
    payload: RateMaterialAssetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    asset = await _service(db).rate_asset(
        user["id"],
        asset_id,
        rating=payload.effect_rating,
        note=payload.effect_rating_note,
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="material_asset_not_found")
    return asset


@router.post("/{asset_id}/reuse")
async def reuse_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    workflow = await WorkflowService(db).create_workflow_from_material(
        asset_id=asset_id,
        owner_user_id=user["id"],
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="material_asset_not_found")
    return workflow


@router.post("/{asset_id}/upload")
async def upload_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    asset = await _service(db).mark_uploaded(user["id"], asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="material_asset_not_found")
    return asset


@router.post("/texts")
async def create_text_asset(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    return await _service(db).create_asset(user["id"], mediaType="text", title="text_prompt", assetType="free")


@router.post("/images")
async def create_image_asset(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    return await _service(db).create_asset(user["id"], mediaType="image", title="image.png", assetType="free")


@router.post("/videos")
async def create_video_asset(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    return await _service(db).create_asset(user["id"], mediaType="video", title="video.mp4", assetType="free")
