from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import get_db
from backend.schemas.credit import CreditSummaryResponse, CreditTransactionPageResponse
from backend.services.credit_service import CreditService

router = APIRouter(prefix="/api/v3/credits", tags=["credits"])


@router.get("", response_model=CreditSummaryResponse)
async def credits(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request)
    if not user:
        return CreditSummaryResponse()
    credit_service = CreditService(db)
    return await credit_service.current_user_credits(user["id"], user.get("role", "USER"))


@router.get("/transactions", response_model=CreditTransactionPageResponse)
async def credit_transactions(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    credit_service = CreditService(db)
    return await credit_service.list_transactions_page(user["id"], offset, limit)
