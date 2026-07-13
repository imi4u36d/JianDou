"""Admin-facing credit user directory queries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit import SysCreditAccount, SysCreditTransaction
from backend.models.user import SysUser
from backend.services.credit_presenters import credit_user_to_dict


class CreditUserDirectory:
    def __init__(
        self,
        db: AsyncSession,
        ensure_account_balance: Callable[[int, int], Awaitable[None]],
        initial_balance: int,
    ) -> None:
        self._db = db
        self._ensure_account_balance = ensure_account_balance
        self._initial_balance = initial_balance

    async def list_users(self, q: str = "", only_ids: set[int] | None = None) -> list[dict]:
        statement = select(SysUser).where(SysUser.username != "admin")
        keyword = q.strip().lower() if q else ""
        if keyword:
            statement = statement.where(SysUser.username.like(f"%{keyword}%"))
        if only_ids:
            statement = statement.where(SysUser.id.in_(only_ids))
        statement = statement.order_by(SysUser.created_at.desc())
        result = await self._db.execute(statement)
        users = result.scalars().all()

        for user in users:
            await self._ensure_account_balance(user.id, self._initial_balance)
        await self._db.commit()
        if not users:
            return []

        user_ids = [user.id for user in users]
        accounts = await self._account_map(user_ids)
        usage_stats = await self._usage_stats(user_ids)
        return [credit_user_to_dict(user, accounts.get(user.id), usage_stats.get(user.id)) for user in users]

    async def _account_map(self, user_ids: list[int]) -> dict[int, SysCreditAccount]:
        result = await self._db.execute(
            select(SysCreditAccount).where(SysCreditAccount.user_id.in_(user_ids))
        )
        return {account.user_id: account for account in result.scalars().all()}

    async def _usage_stats(self, user_ids: list[int]) -> dict[int, dict]:
        result = await self._db.execute(
            select(SysCreditTransaction)
            .where(
                SysCreditTransaction.user_id.in_(user_ids),
                SysCreditTransaction.transaction_type.in_(["CONSUME", "USAGE"]),
            )
            .order_by(SysCreditTransaction.created_at.asc())
        )
        stats_map: dict[int, dict] = {}
        for transaction in result.scalars().all():
            stats = stats_map.setdefault(transaction.user_id, {
                "imageGenerationCount": 0,
                "videoGenerationCount": 0,
                "lastUsedAt": None,
            })
            feature_code = str(transaction.feature_code or "").strip().upper()
            if feature_code == "IMAGE_GENERATION":
                stats["imageGenerationCount"] += 1
            if feature_code == "VIDEO_GENERATION":
                stats["videoGenerationCount"] += 1
            if transaction.created_at and (stats["lastUsedAt"] is None or transaction.created_at > stats["lastUsedAt"]):
                stats["lastUsedAt"] = transaction.created_at
        return stats_map
