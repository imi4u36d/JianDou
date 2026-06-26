from __future__ import annotations

from pydantic import BaseModel, Field


class CreditSummaryResponse(BaseModel):
    exempt: bool = False
    balance: int | None = None
    totalConsumed: int = 0
    totalAdjusted: int = 0
    rules: list = Field(default_factory=list)


class CreditTransactionResponse(BaseModel):
    transactionId: str
    userId: int
    featureCode: str | None = ""
    transactionType: str
    amountDelta: int = 0
    balanceBefore: int = 0
    balanceAfter: int = 0
    relatedRunId: str | None = ""
    relatedTaskId: str | None = ""
    relatedWorkflowId: str | None = ""
    reason: str | None = ""
    metadata: dict = Field(default_factory=dict)
    createdAt: str


class CreditTransactionPageResponse(BaseModel):
    items: list[CreditTransactionResponse] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 20


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
    last_used_at: str | None = None

class CreditAdjustmentRequest(BaseModel):
    amount: int
    reason: str = ""

class CreditRuleUpdateRequest(BaseModel):
    cost: int
