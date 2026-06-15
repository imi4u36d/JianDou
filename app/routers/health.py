from __future__ import annotations
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["health"])

@router.get("/api/v3/health")
async def health():
    return {"healthy": True, "env": settings.app_env, "executionMode": settings.execution_mode}
