from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api/v3/material-assets", tags=["material-assets"])

_materials: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _material_item(asset_id: str, **overrides):
    now = _now_iso()
    item = {
        "id": asset_id,
        "workflowId": None,
        "stageType": "material",
        "clipIndex": 0,
        "versionNo": 1,
        "selectedForNext": False,
        "assetType": "free",
        "assetRole": None,
        "userRating": None,
        "ratingNote": None,
        "mediaType": "image",
        "title": "素材",
        "originModel": None,
        "originProvider": None,
        "mimeType": None,
        "durationSeconds": None,
        "width": None,
        "height": None,
        "hasAudio": False,
        "fileUrl": "",
        "previewUrl": "",
        "thumbnailUrl": None,
        "remoteUrl": None,
        "hasRemotePath": False,
        "remotePath": None,
        "metadata": {},
        "createdAt": now,
        "updatedAt": now,
        "status": "ready",
    }
    item.update(overrides)
    return item


def upsert_material_asset(asset_id: str | None = None, **overrides):
    resolved_id = asset_id or f"mat_{uuid.uuid4().hex}"
    existing = _materials.get(resolved_id)
    if existing:
        updated = {**existing, **overrides, "updatedAt": _now_iso()}
    else:
        updated = _material_item(resolved_id, **overrides)
    _materials[resolved_id] = updated
    return updated


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
    return upsert_material_asset(title="stub", mediaType="text", assetType="free")


@router.get("/{asset_id}")
async def get_material_asset(asset_id: str):
    asset = _materials.get(asset_id)
    if asset:
        return asset
    return upsert_material_asset(asset_id, title="stub", mediaType="text", assetType="free")


@router.delete("/{asset_id}")
async def delete_material_asset(asset_id: str):
    _materials.pop(asset_id, None)
    return {"deleted": True, "assetId": asset_id}


@router.patch("/{asset_id}/rating")
async def rate_material_asset(asset_id: str, request: Request):
    body = await request.json()
    asset = _materials.get(asset_id) or upsert_material_asset(asset_id)
    asset["userRating"] = body.get("effectRating")
    asset["ratingNote"] = body.get("effectRatingNote")
    asset["updatedAt"] = _now_iso()
    _materials[asset_id] = asset
    return asset


@router.post("/{asset_id}/reuse")
async def reuse_material_asset(asset_id: str):
    asset = _materials.get(asset_id) or upsert_material_asset(asset_id)
    workflow_id = f"wf_{uuid.uuid4().hex}"
    now = _now_iso()
    return {
        "id": workflow_id,
        "title": f"{asset.get('title') or '素材'}复用",
        "transcriptText": "",
        "aspectRatio": "16:9",
        "stylePreset": None,
        "textAnalysisModel": "",
        "imageModel": "",
        "videoModel": "",
        "videoSize": None,
        "keyframeSeed": None,
        "videoSeed": None,
        "seed": None,
        "durationMode": "auto",
        "minDurationSeconds": None,
        "maxDurationSeconds": None,
        "status": "draft",
        "currentStage": "storyboard",
        "selectedStoryboardVersionId": None,
        "effectRating": None,
        "effectRatingNote": None,
        "ratedAt": None,
        "createdAt": now,
        "updatedAt": now,
        "storyboardVersions": [],
        "characterSheets": [],
        "clipSlots": [],
        "finalResult": asset,
    }


@router.post("/{asset_id}/upload")
async def upload_material_asset(asset_id: str):
    asset = _materials.get(asset_id) or upsert_material_asset(asset_id)
    asset["status"] = "ready"
    asset["updatedAt"] = _now_iso()
    _materials[asset_id] = asset
    return asset


@router.post("/texts")
async def create_text_asset():
    return upsert_material_asset(mediaType="text", title="text_prompt", assetType="free")


@router.post("/images")
async def create_image_asset():
    return upsert_material_asset(mediaType="image", title="image.png", assetType="free")


@router.post("/videos")
async def create_video_asset():
    return upsert_material_asset(mediaType="video", title="video.mp4", assetType="free")
