from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class CreditSummaryResponse(BaseModel):
    exempt: bool = False
    balance: Optional[int] = None
    rules: list = []

class AdminCreditUserResponse(BaseModel):
    id: int
    username: str = ""
    display_name: str = ""
    role: str = ""
    status: str = ""
    balance: int = 0
    total_consumed: int = 0
    total_adjusted: int = 0
    image_generation_count: int = 0
    video_generation_count: int = 0
    last_used_at: Optional[str] = None

class CreditAdjustmentRequest(BaseModel):
    amount: int
    reason: str = ""

class CreditRuleUpdateRequest(BaseModel):
    cost: int
