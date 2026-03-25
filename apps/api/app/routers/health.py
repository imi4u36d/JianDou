from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    return {
        "ok": True,
        "runtime": request.app.state.runtime.describe(),
    }
