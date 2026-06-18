from __future__ import annotations
from fastapi import APIRouter, Request

from backend.routers.material_assets import upsert_material_asset

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
async def create_material_generation(request: Request):
    body = await request.json()
    title = str(body.get("title") or "素材生成").strip()
    asset_type = str(body.get("assetType") or "free").strip()
    asset = upsert_material_asset(
        title=title,
        assetType=asset_type,
        mediaType="image",
        metadata={
            "description": body.get("description"),
            "styleKeywords": body.get("styleKeywords") or [],
            "aspectRatio": body.get("aspectRatio"),
            "imageSize": body.get("imageSize"),
            "textAnalysisModel": body.get("textAnalysisModel"),
            "imageModel": body.get("imageModel"),
            "seed": body.get("seed"),
        },
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
