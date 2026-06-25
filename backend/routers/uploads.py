from __future__ import annotations

import logging

from fastapi import APIRouter, File, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.errors import bad_request
from backend.schemas.upload import UploadAssetResponse
from backend.services.object_storage import create_upload_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/uploads", tags=["uploads"])

CHUNK_SIZE = 64 * 1024  # 64 KB


async def _read_with_limit(file: UploadFile) -> bytes:
    """Read an upload file respecting the configured size limit.

    Reads in chunks to avoid loading excessively large files into memory
    in one allocation.  Raises ``HTTPException(413)`` if the file exceeds
    ``settings.upload_max_size_bytes``.
    """
    max_bytes = settings.upload_max_size_bytes
    buffer = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise bad_request(f"文件大小超过限制（最大 {max_bytes // (1024 * 1024)} MB）")
    return bytes(buffer)


async def _store_upload(media_type: str, file: UploadFile) -> UploadAssetResponse:
    content = await _read_with_limit(file)
    file_name = file.filename or ""
    stored = await run_in_threadpool(
        create_upload_storage(settings).store_upload,
        media_type,
        file_name,
        content,
        file.content_type or "",
    )
    return UploadAssetResponse(
        asset_id=stored.asset_id,
        file_name=stored.file_name,
        file_url=stored.public_url,
        public_url=stored.public_url,
        size_bytes=stored.size_bytes,
    )


@router.post("/texts", response_model=UploadAssetResponse)
async def upload_text(file: UploadFile = File(...)):
    return await _store_upload("texts", file)


@router.post("/videos", response_model=UploadAssetResponse)
async def upload_video(file: UploadFile = File(...)):
    return await _store_upload("videos", file)


@router.post("/images", response_model=UploadAssetResponse)
async def upload_image(file: UploadFile = File(...)):
    return await _store_upload("images", file)
