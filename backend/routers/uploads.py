from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/api/v3/uploads", tags=["uploads"])


@router.post("/texts")
async def upload_text(file: UploadFile = File(...)):
    content = await file.read()
    return {
        "asset_id": f"asset_{len(content)}",
        "file_name": file.filename or "",
        "file_url": "",
        "public_url": "",
        "size_bytes": len(content),
    }


@router.post("/videos")
async def upload_video(file: UploadFile = File(...)):
    content = await file.read()
    return {
        "asset_id": f"asset_{len(content)}",
        "file_name": file.filename or "",
        "file_url": "",
        "public_url": "",
        "size_bytes": len(content),
    }


@router.post("/images")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()
    return {
        "asset_id": f"asset_{len(content)}",
        "file_name": file.filename or "",
        "file_url": "",
        "public_url": "",
        "size_bytes": len(content),
    }
