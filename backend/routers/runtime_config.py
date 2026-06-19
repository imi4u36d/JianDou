from __future__ import annotations

from fastapi import APIRouter

from backend.config import settings

router = APIRouter(tags=["runtime-config"])

@router.get("/runtime-config.json")
async def runtime_config():
    return {
        "apiBaseUrl": settings.public_api_base_url,
        "storageBaseUrl": settings.public_storage_base_url,
        "adminBaseUrl": settings.public_admin_base_url,
    }
