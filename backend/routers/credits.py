from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import get_db
from backend.services.credit_service import CreditService

router = APIRouter(prefix="/api/v3/auth", tags=["credits"])


@router.get("/credits")
async def credits(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request)
    if not user:
        return {"exempt": False, "balance": 0, "totalConsumed": 0, "totalAdjusted": 0, "rules": []}
    credit_service = CreditService(db)
    result = await credit_service.current_user_credits(user["id"], user.get("role", "USER"))
    return result
