from __future__ import annotations

from pydantic import BaseModel


class UploadAssetResponse(BaseModel):
    asset_id: str
    file_name: str = ""
    file_url: str = ""
    public_url: str = ""
    size_bytes: int = 0
