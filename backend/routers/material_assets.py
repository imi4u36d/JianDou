from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.errors import bad_request, conflict, not_found, service_unavailable
from backend.schemas.material import (
    CreateMaterialFavoriteFolderRequest,
    MaterialAssetDeleteResult,
    MaterialFavoriteAssetIdsRequest,
    MaterialFavoriteFolder,
    MaterialFavoriteFolderDeleteResult,
    MaterialFavoriteFolderList,
    RateMaterialAssetRequest,
    RenameMaterialFavoriteFolderRequest,
)
from backend.services.material_asset_service import MaterialAssetService
from backend.services.material_favorite_service import MaterialFavoriteService
from backend.services.workflow_service import WorkflowService

router = APIRouter(prefix="/api/v3/material-assets", tags=["material-assets"])
logger = logging.getLogger(__name__)


def _service(db: AsyncSession) -> MaterialAssetService:
    return MaterialAssetService(db)


def _favorite_service(request: Request) -> MaterialFavoriteService:
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
        raise service_unavailable("redis_unavailable")
    return MaterialFavoriteService(redis_client)


async def _verify_owned_asset_ids(db: AsyncSession, owner_user_id: int, asset_ids: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for asset_id in asset_ids:
        value = asset_id.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        asset = await _service(db).get_asset(owner_user_id, value)
        if asset is None:
            raise not_found("material_asset")
        cleaned.append(value)
    return cleaned


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
    includeWorkflowArtifacts: bool = Query(default=False),
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
        include_workflow_artifacts=includeWorkflowArtifacts,
    )


@router.post("")
async def create_material_asset(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    return await _service(db).create_asset(user["id"], title="素材", mediaType="text", assetType="free")


@router.get("/favorite-folders", response_model=MaterialFavoriteFolderList)
async def list_material_favorite_folders(request: Request):
    user = await require_user(request)
    folders = await _favorite_service(request).list_folders(user["id"])
    return MaterialFavoriteFolderList(folders=folders)


@router.post("/favorite-folders", response_model=MaterialFavoriteFolder)
async def create_material_favorite_folder(
    payload: CreateMaterialFavoriteFolderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    name = payload.name.strip()
    if not name:
        raise bad_request("favorite_folder_name_required")
    asset_ids = await _verify_owned_asset_ids(db, user["id"], payload.asset_ids)
    try:
        return await _favorite_service(request).create_folder(user["id"], name=name, asset_ids=asset_ids)
    except ValueError as exc:
        if str(exc) == "favorite_folder_name_exists":
            raise conflict("favorite_folder_name_exists") from exc
        raise


@router.patch("/favorite-folders/{folder_id}", response_model=MaterialFavoriteFolder)
async def rename_material_favorite_folder(
    folder_id: str,
    payload: RenameMaterialFavoriteFolderRequest,
    request: Request,
):
    user = await require_user(request)
    name = payload.name.strip()
    if not name:
        raise bad_request("favorite_folder_name_required")
    try:
        folder = await _favorite_service(request).rename_folder(user["id"], folder_id, name=name)
    except ValueError as exc:
        if str(exc) == "favorite_folder_name_exists":
            raise conflict("favorite_folder_name_exists") from exc
        raise
    if folder is None:
        raise not_found("material_favorite_folder")
    return folder


@router.delete("/favorite-folders/{folder_id}", response_model=MaterialFavoriteFolderDeleteResult)
async def delete_material_favorite_folder(folder_id: str, request: Request):
    user = await require_user(request)
    deleted = await _favorite_service(request).delete_folder(user["id"], folder_id)
    if not deleted:
        raise not_found("material_favorite_folder")
    return MaterialFavoriteFolderDeleteResult(deleted=True, folder_id=folder_id)


@router.post("/favorite-folders/{folder_id}/assets", response_model=MaterialFavoriteFolder)
async def add_material_favorite_assets(
    folder_id: str,
    payload: MaterialFavoriteAssetIdsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    asset_ids = await _verify_owned_asset_ids(db, user["id"], payload.asset_ids)
    if not asset_ids:
        raise bad_request("favorite_asset_ids_required")
    folder = await _favorite_service(request).add_assets(user["id"], folder_id, asset_ids)
    if folder is None:
        raise not_found("material_favorite_folder")
    return folder


@router.delete("/favorite-folders/{folder_id}/assets/{asset_id}", response_model=MaterialFavoriteFolder)
async def remove_material_favorite_asset(folder_id: str, asset_id: str, request: Request):
    user = await require_user(request)
    folder = await _favorite_service(request).remove_asset(user["id"], folder_id, asset_id)
    if folder is None:
        raise not_found("material_favorite_folder")
    return folder


@router.get("/{asset_id}")
async def get_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    asset = await _service(db).get_asset(user["id"], asset_id)
    if asset is None:
        raise not_found("material_asset")
    return asset


@router.delete("/{asset_id}", response_model=MaterialAssetDeleteResult)
async def delete_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    deleted = await _service(db).delete_asset(user["id"], asset_id)
    if not deleted:
        raise not_found("material_asset")
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is not None:
        try:
            await MaterialFavoriteService(redis_client).remove_asset_from_all(user["id"], asset_id)
        except Exception as exc:
            logger.warning("Failed to remove deleted material asset from favorites: %s", exc)
    return MaterialAssetDeleteResult(deleted=True, asset_id=asset_id)


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
        raise not_found("material_asset")
    return asset


@router.post("/{asset_id}/reuse")
async def reuse_material_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a workflow from an existing material instead of cloning it client-side."""
    user = await require_user(request)
    payload: dict[str, Any] = {}
    try:
        parsed = await request.json()
    except Exception:
        parsed = {}
    if isinstance(parsed, dict):
        payload = parsed
    workflow = await WorkflowService(db).create_workflow_from_material(
        asset_id=asset_id,
        owner_user_id=user["id"],
        mode=str(payload.get("mode") or "clone"),
    )
    if workflow is None:
        raise not_found("material_asset")
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
        raise not_found("material_asset")
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
