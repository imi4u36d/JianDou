from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.database import get_db
from backend.schemas.material import CreateMaterialGenerationRequest
from backend.services.material_asset_service import MaterialAssetService

router = APIRouter(prefix="/api/v3/material-center", tags=["material-center"])


@router.get("/categories")
async def list_categories():
    return []


@router.get("/library")
async def list_library():
    return []


@router.get("/search")
async def search_materials():
    return []


@router.post("/generations")
async def create_material_generation(
    payload: CreateMaterialGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await require_user(request)
    title = payload.title.strip() or "素材生成"
    asset_type = payload.asset_type.strip() or "free"
    asset = await MaterialAssetService(db).create_asset(
        user["id"],
        title=title,
        assetType=asset_type,
        mediaType="image",
        metadata=payload.metadata(),
    )
    return {
        "id": asset["id"],
        "asset": asset,
        "assets": [asset],
        "outputUrl": asset.get("fileUrl") or None,
        "previewUrl": asset.get("previewUrl") or None,
        "fileUrl": asset.get("fileUrl") or None,
        "title": asset.get("title"),
        "status": asset.get("status", "ready"),
        "metadata": asset.get("metadata") or {},
    }
