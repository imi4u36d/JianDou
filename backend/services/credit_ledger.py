"""Atomic credit balance mutations and transaction history."""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit import SysCreditAccount, SysCreditTransaction
from backend.models.user import SysUser
from backend.services.credit_presenters import transaction_to_dict
from backend.services.credit_rule_catalog import normalize_feature_code
from backend.shared import now_iso

RuleCostResolver = Callable[[str], Awaitable[int]]


class InsufficientCreditsError(ValueError):
    def __init__(self, user_id: int, feature_code: str, cost: int, balance: int) -> None:
        super().__init__(
            f"Insufficient credits: user={user_id}, feature={feature_code}, "
            f"cost={cost}, balance={balance}"
        )
        self.user_id = user_id
        self.feature_code = feature_code
        self.cost = cost
        self.balance = balance


class CreditLedger:
    """Own atomic balance changes and their audit rows."""

    def __init__(self, db: AsyncSession, rule_cost: RuleCostResolver, initial_balance: int) -> None:
        self._db = db
        self._rule_cost = rule_cost
        self._initial_balance = initial_balance

    async def list_transactions(self, user_id: int) -> list[dict]:
        result = await self._db.execute(
            select(SysCreditTransaction)
            .where(SysCreditTransaction.user_id == user_id)
            .order_by(SysCreditTransaction.created_at.desc())
            .limit(200)
        )
        return [transaction_to_dict(transaction) for transaction in result.scalars().all()]

    async def list_transactions_page(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> dict:
        normalized_offset = max(0, offset)
        normalized_limit = min(max(1, limit), 50)
        count = await self._db.execute(
            select(func.count())
            .select_from(SysCreditTransaction)
            .where(SysCreditTransaction.user_id == user_id)
        )
        result = await self._db.execute(
            select(SysCreditTransaction)
            .where(SysCreditTransaction.user_id == user_id)
            .order_by(SysCreditTransaction.created_at.desc(), SysCreditTransaction.id.desc())
            .offset(normalized_offset)
            .limit(normalized_limit)
        )
        return {
            "items": [transaction_to_dict(transaction) for transaction in result.scalars().all()],
            "total": int(count.scalar_one() or 0),
            "offset": normalized_offset,
            "limit": normalized_limit,
        }

    async def charge(
        self,
        user_id: int,
        feature_code: str,
        run_id: str = "",
        task_id: str = "",
        workflow_id: str = "",
        reason: str = "",
        commit: bool = True,
    ) -> dict:
        code = normalize_feature_code(feature_code)
        cost = await self._rule_cost(code)
        user = await self._user(user_id)
        if self._is_admin(user):
            return {
                "charged": False,
                "userId": user_id,
                "featureCode": code,
                "cost": cost,
                "balanceBefore": 0,
                "balanceAfter": 0,
                "transactionId": "",
            }
        await self.ensure_account_balance(user_id, self._initial_balance)
        normalized_cost = max(0, cost)
        result = await self._db.execute(
            sa_update(SysCreditAccount)
            .where(
                SysCreditAccount.user_id == user_id,
                SysCreditAccount.balance >= normalized_cost,
            )
            .values(
                balance=SysCreditAccount.balance - normalized_cost,
                total_consumed=SysCreditAccount.total_consumed + normalized_cost,
                updated_at=now_iso(),
            )
        )
        if result.rowcount == 0:
            account = await self.get_account(user_id)
            raise InsufficientCreditsError(
                user_id, code, normalized_cost, account.balance if account else 0
            )
        account = await self.get_account(user_id)
        balance_after = account.balance if account else 0
        balance_before = balance_after + normalized_cost
        transaction_id = await self.record_transaction(
            user_id=user_id,
            feature_code=code,
            transaction_type="CONSUME" if normalized_cost > 0 else "USAGE",
            amount_delta=-normalized_cost,
            balance_before=balance_before,
            balance_after=balance_after,
            run_id=run_id,
            task_id=task_id,
            workflow_id=workflow_id,
            reason=reason,
        )
        await (self._db.commit() if commit else self._db.flush())
        return {
            "charged": True,
            "userId": user_id,
            "featureCode": code,
            "cost": normalized_cost,
            "balanceBefore": balance_before,
            "balanceAfter": balance_after,
            "transactionId": transaction_id,
        }

    async def refund(
        self,
        user_id: int,
        feature_code: str,
        amount: int,
        run_id: str = "",
        task_id: str = "",
        workflow_id: str = "",
        reason: str = "",
    ) -> bool:
        normalized_amount = max(0, amount)
        if user_id is None or normalized_amount <= 0:
            return False
        await self.ensure_account_balance(user_id, self._initial_balance)
        account = await self.get_account(user_id)
        balance_before = account.balance if account else 0
        balance_after = balance_before + normalized_amount
        await self._db.execute(
            sa_update(SysCreditAccount)
            .where(SysCreditAccount.user_id == user_id)
            .values(balance=balance_after, updated_at=now_iso())
        )
        await self.record_transaction(
            user_id=user_id,
            feature_code=normalize_feature_code(feature_code),
            transaction_type="REFUND",
            amount_delta=normalized_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            run_id=run_id,
            task_id=task_id,
            workflow_id=workflow_id,
            reason=reason,
        )
        await self._db.commit()
        return True

    async def adjust(self, user_id: int, amount: int, reason: str) -> None:
        if amount == 0:
            raise ValueError("调整积分不能为 0")
        if not reason.strip():
            raise ValueError("调整原因不能为空")
        user = await self._user(user_id)
        if self._is_admin_username(user.username):
            raise ValueError("admin 账号不参与积分调整")
        await self.ensure_account_balance(user_id, self._initial_balance)
        account = await self.get_account(user_id)
        balance_before = account.balance if account else 0
        balance_after = balance_before + amount
        if balance_after < 0:
            raise ValueError("调整后积分不能小于 0")
        await self._db.execute(
            sa_update(SysCreditAccount)
            .where(SysCreditAccount.user_id == user_id)
            .values(
                balance=balance_after,
                total_adjusted=(account.total_adjusted if account else 0) + amount,
                updated_at=now_iso(),
            )
        )
        await self.record_transaction(
            user_id=user_id,
            feature_code="",
            transaction_type="ADJUST",
            amount_delta=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason.strip(),
        )
        await self._db.commit()

    async def get_account(self, user_id: int) -> SysCreditAccount | None:
        result = await self._db.execute(
            select(SysCreditAccount).where(SysCreditAccount.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def account_balance(self, user_id: int) -> dict:
        account = await self.get_account(user_id)
        if not account:
            return {"balance": 0, "totalConsumed": 0, "totalAdjusted": 0}
        return {
            "balance": account.balance or 0,
            "totalConsumed": account.total_consumed or 0,
            "totalAdjusted": account.total_adjusted or 0,
        }

    async def ensure_account_balance(self, user_id: int, initial_balance: int) -> None:
        if await self.get_account(user_id):
            return
        now = now_iso()
        self._db.add(
            SysCreditAccount(
                user_id=user_id,
                balance=max(0, initial_balance),
                total_consumed=0,
                total_adjusted=0,
                created_at=now,
                updated_at=now,
            )
        )
        await self._db.flush()

    async def record_transaction(
        self,
        user_id: int,
        feature_code: str,
        transaction_type: str,
        amount_delta: int,
        balance_before: int,
        balance_after: int,
        run_id: str = "",
        task_id: str = "",
        workflow_id: str = "",
        reason: str = "",
        metadata: dict | None = None,
    ) -> str:
        transaction_id = "credit_" + uuid.uuid4().hex
        self._db.add(
            SysCreditTransaction(
                transaction_id=transaction_id,
                user_id=user_id,
                feature_code=normalize_feature_code(feature_code),
                transaction_type=transaction_type,
                amount_delta=amount_delta,
                balance_before=balance_before,
                balance_after=balance_after,
                related_run_id=run_id.strip(),
                related_task_id=task_id.strip(),
                related_workflow_id=workflow_id.strip(),
                reason=reason.strip(),
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
                created_at=now_iso(),
            )
        )
        await self._db.flush()
        return transaction_id

    async def _user(self, user_id: int) -> SysUser:
        result = await self._db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("user_not_found")
        return user

    @classmethod
    def _is_admin(cls, user: SysUser) -> bool:
        return cls._is_admin_username(user.username) or str(user.role or "").strip().upper() == "ADMIN"

    @staticmethod
    def _is_admin_username(username: str) -> bool:
        return username.strip().lower() == "admin" if username else False
