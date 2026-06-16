from __future__ import annotations
from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api/v3/material-assets", tags=["material-assets"])

_materials: dict[str, dict] = {}


@router.get("")
async def list_material_assets(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=200),
):
    all_items = list(_materials.values())
    total = len(all_items)
    items = all_items[offset : offset + limit]
    next_offset = offset + limit if offset + limit < total else None
    return {
        "items": items,
        "offset": offset,
        "limit": limit,
        "total": total,
        "hasMore": next_offset is not None,
        "nextOffset": next_offset,
    }


@router.post("")
async def create_material_asset():
    return {"asset_id": "stub", "title": "stub", "asset_type": "text", "status": "ready"}


@router.get("/{asset_id}")
async def get_material_asset(asset_id: str):
    asset = _materials.get(asset_id)
    if asset:
        return asset
    return {"asset_id": asset_id, "title": "stub", "asset_type": "text", "status": "ready"}


@router.delete("/{asset_id}")
async def delete_material_asset(asset_id: str):
    _materials.pop(asset_id, None)
    return {"success": True, "asset_id": asset_id}


@router.post("/texts")
async def create_text_asset():
    return {"asset_id": "text_stub", "file_name": "text_prompt", "content_preview": "", "size_bytes": 0}


@router.post("/images")
async def create_image_asset():
    return {"asset_id": "img_stub", "file_name": "image.png", "file_url": "", "size_bytes": 0}


@router.post("/videos")
async def create_video_asset():
    return {"asset_id": "vid_stub", "file_name": "video.mp4", "file_url": "", "size_bytes": 0}
