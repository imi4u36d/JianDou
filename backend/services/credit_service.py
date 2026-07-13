"""Credit application facade for accounts, rules, ledger mutations, and users."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit import SysCreditAccount
from backend.models.user import SysUser
from backend.services.credit_ledger import CreditLedger, InsufficientCreditsError
from backend.services.credit_presenters import account_to_dict, credit_user_to_dict
from backend.services.credit_rule_catalog import (
    DEFAULT_CREDIT_RULES,
    IMAGE_GENERATION,
    VIDEO_GENERATION,
    CreditRuleCatalog,
    normalize_feature_code,
)
from backend.services.credit_user_directory import CreditUserDirectory
from backend.shared import now_iso

DEFAULT_INITIAL_BALANCE = 50

__all__ = [
    "DEFAULT_CREDIT_RULES",
    "DEFAULT_INITIAL_BALANCE",
    "IMAGE_GENERATION",
    "InsufficientCreditsError",
    "VIDEO_GENERATION",
    "CreditService",
    "normalize_feature_code",
]


def _is_admin_username(username: str) -> bool:
    return username.strip().lower() == "admin" if username else False


def _is_admin_user(user: SysUser) -> bool:
    return _is_admin_username(user.username) or str(user.role or "").strip().upper() == "ADMIN"


class CreditService:
    """Stable credit facade composed from focused persistence collaborators."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._rules = CreditRuleCatalog(db)
        self._ledger = CreditLedger(db, self._rules.rule_cost, DEFAULT_INITIAL_BALANCE)
        self._user_directory = CreditUserDirectory(
            db,
            self._ledger.ensure_account_balance,
            DEFAULT_INITIAL_BALANCE,
        )

    async def ensure_account(
        self, user_id: int, initial_balance: int = DEFAULT_INITIAL_BALANCE
    ) -> dict:
        if user_id is None:
            raise ValueError("user_id is required")
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("user_not_found")
        if _is_admin_user(user):
            return {"created": False, "reason": "admin_skipped"}
        if await self._ledger.get_account(user_id):
            return {"created": False, "reason": "already_exists"}
        now = now_iso()
        account = SysCreditAccount(
            user_id=user_id,
            balance=max(0, initial_balance),
            total_consumed=0,
            total_adjusted=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return {"created": True, "account": account_to_dict(account)}

    async def current_user_credits(self, user_id: int, role: str) -> dict:
        exempt = role == "ADMIN"
        balance = (
            {"balance": 0, "totalConsumed": 0, "totalAdjusted": 0}
            if exempt
            else await self._ledger.account_balance(user_id)
        )
        return {
            "exempt": exempt,
            "balance": balance["balance"],
            "totalConsumed": balance["totalConsumed"],
            "totalAdjusted": balance["totalAdjusted"],
            "rules": await self.list_rules(),
        }

    async def list_rules(self) -> list[dict]:
        return await self._rules.list_rules()

    async def update_rule(self, feature_code: str, cost: int) -> dict | None:
        return await self._rules.update_rule(feature_code, cost)

    async def list_transactions(self, user_id: int) -> list[dict]:
        return await self._ledger.list_transactions(user_id)

    async def list_transactions_page(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> dict:
        return await self._ledger.list_transactions_page(user_id, offset, limit)

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
        return await self._ledger.charge(
            user_id,
            feature_code,
            run_id,
            task_id,
            workflow_id,
            reason,
            commit,
        )

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
        return await self._ledger.refund(
            user_id,
            feature_code,
            amount,
            run_id,
            task_id,
            workflow_id,
            reason,
        )

    async def adjust(self, user_id: int, amount: int, reason: str) -> dict | None:
        await self._ledger.adjust(user_id, amount, reason)
        users = await self.list_users("", only_ids={user_id})
        return users[0] if users else None

    async def list_users(
        self, q: str = "", only_ids: set[int] | None = None
    ) -> list[dict]:
        return await self._user_directory.list_users(q, only_ids)

    async def _get_account(self, user_id: int) -> SysCreditAccount | None:
        return await self._ledger.get_account(user_id)

    async def _account_balance(self, user_id: int) -> dict:
        return await self._ledger.account_balance(user_id)

    async def _rule_cost(self, feature_code: str) -> int:
        return await self._rules.rule_cost(feature_code)

    async def _ensure_default_rules(self) -> None:
        await self._rules.ensure_defaults()

    async def _ensure_account_balance(self, user_id: int, initial_balance: int) -> None:
        await self._ledger.ensure_account_balance(user_id, initial_balance)

    async def _record_transaction(self, **kwargs) -> str:  # noqa: ANN003
        return await self._ledger.record_transaction(**kwargs)

    @staticmethod
    def _default_rule_name(feature_code: str) -> str:
        return CreditRuleCatalog.default_rule_name(feature_code)

    @staticmethod
    def _account_to_dict(account: SysCreditAccount) -> dict:
        return account_to_dict(account)

    @staticmethod
    def _to_credit_user_dict(user: SysUser, account, stats: dict | None) -> dict:  # noqa: ANN001
        return credit_user_to_dict(user, account, stats)
