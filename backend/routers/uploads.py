from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from backend.config import settings
from backend.errors import bad_request
from backend.schemas.upload import UploadAssetResponse

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


def _asset_response(content: bytes, file_name: str) -> UploadAssetResponse:
    return UploadAssetResponse(
        asset_id=f"asset_{len(content)}",
        file_name=file_name,
        size_bytes=len(content),
    )


@router.post("/texts", response_model=UploadAssetResponse)
async def upload_text(file: UploadFile = File(...)):
    content = await _read_with_limit(file)
    return _asset_response(content, file.filename or "")


@router.post("/videos", response_model=UploadAssetResponse)
async def upload_video(file: UploadFile = File(...)):
    content = await _read_with_limit(file)
    return _asset_response(content, file.filename or "")


@router.post("/images", response_model=UploadAssetResponse)
async def upload_image(file: UploadFile = File(...)):
    content = await _read_with_limit(file)
    return _asset_response(content, file.filename or "")
