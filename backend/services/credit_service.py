from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit import (
    SysCreditAccount,
    SysCreditRule,
    SysCreditTransaction,
)
from backend.models.user import SysUser

DEFAULT_INITIAL_BALANCE = 50


# 功能编码常量
IMAGE_GENERATION = "IMAGE_GENERATION"
VIDEO_GENERATION = "VIDEO_GENERATION"


def normalize_feature_code(code: str) -> str:
    return code.strip().upper() if code else ""


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trim(value: str | None) -> str:
    return value.strip() if value else ""


def _is_admin_username(username: str) -> bool:
    return username.strip().lower() == "admin" if username else False


class CreditService:
    """积分服务 —— 积分账户管理、扣费、退款、调整、规则管理。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 账户创建 ──────────────────────────────────────────────────

    async def ensure_account(self, user_id: int, initial_balance: int = DEFAULT_INITIAL_BALANCE) -> dict:
        """为用户创建积分账户（如果不存在）。跳过 admin。"""
        if user_id is None:
            raise ValueError("user_id is required")

        # 检查用户是否存在且不是 admin
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("user_not_found")

        if _is_admin_username(user.username):
            return {"created": False, "reason": "admin_skipped"}

        # 检查账户是否已存在
        result = await self.db.execute(
            select(SysCreditAccount).where(SysCreditAccount.user_id == user_id).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {"created": False, "reason": "already_exists"}

        now = _now_str()
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
        return {"created": True, "account": self._account_to_dict(account)}

    # ── 查询 ──────────────────────────────────────────────────────

    async def current_user_credits(self, user_id: int, role: str) -> dict:
        """获取当前用户的积分信息及规则列表。admin 豁免。"""
        exempt = role == "ADMIN"
        if not exempt:
            balance = await self._account_balance(user_id)
        else:
            balance = {"balance": 0, "totalConsumed": 0, "totalAdjusted": 0}

        rules = await self.list_rules()
        return {
            "exempt": exempt,
            "balance": balance["balance"],
            "totalConsumed": balance["totalConsumed"],
            "totalAdjusted": balance["totalAdjusted"],
            "rules": rules,
        }

    async def list_rules(self) -> list[dict]:
        """列出所有积分规则。"""
        result = await self.db.execute(
            select(SysCreditRule).order_by(SysCreditRule.feature_code.asc())
        )
        return [self._rule_to_dict(r) for r in result.scalars().all()]

    async def update_rule(self, feature_code: str, cost: int) -> Optional[dict]:
        """更新或创建积分规则。"""
        if cost < 0:
            raise ValueError("积分消耗值必须为非负整数")

        _code = normalize_feature_code(feature_code)
        if not _code:
            raise ValueError("功能编码不能为空")

        result = await self.db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == _code).limit(1)
        )
        existing = result.scalar_one_or_none()
        now = _now_str()

        if existing:
            await self.db.execute(
                sa_update(SysCreditRule)
                .where(SysCreditRule.feature_code == _code)
                .values(cost=max(0, cost), updated_at=now)
            )
        else:
            display_name = self._default_rule_name(_code)
            rule = SysCreditRule(
                feature_code=_code,
                display_name=display_name,
                cost=max(0, cost),
                created_at=now,
                updated_at=now,
            )
            self.db.add(rule)
        await self.db.commit()

        # 重新查询
        result = await self.db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == _code).limit(1)
        )
        updated = result.scalar_one_or_none()
        return self._rule_to_dict(updated) if updated else None

    async def list_transactions(self, user_id: int) -> list[dict]:
        """列出用户的积分交易记录（最多 200 条）。"""
        result = await self.db.execute(
            select(SysCreditTransaction)
            .where(SysCreditTransaction.user_id == user_id)
            .order_by(SysCreditTransaction.created_at.desc())
            .limit(200)
        )
        return [self._transaction_to_dict(t) for t in result.scalars().all()]

    # ── 扣费 / 退款 / 调整 ───────────────────────────────────────

    async def charge(
        self, user_id: int, feature_code: str, run_id: str = "",
        task_id: str = "", workflow_id: str = "", reason: str = "",
    ) -> dict:
        """
        扣除用户积分。如果余额不足，抛出 ValueError。
        返回 charge 结果 dict。
        """
        _code = normalize_feature_code(feature_code)
        cost = await self._rule_cost(_code)

        # admin 豁免
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("user_not_found")
        if _is_admin_username(user.username):
            return {
                "charged": False,
                "userId": user_id,
                "featureCode": _code,
                "cost": cost,
                "balanceBefore": 0,
                "balanceAfter": 0,
                "transactionId": "",
            }

        # 确保账户存在
        await self._ensure_account_balance(user_id, DEFAULT_INITIAL_BALANCE)

        # 原子扣费：balance = balance - cost，要求 balance >= cost
        normalized_cost = max(0, cost)
        stmt = (
            sa_update(SysCreditAccount)
            .where(
                SysCreditAccount.user_id == user_id,
                SysCreditAccount.balance >= normalized_cost,
            )
            .values(
                balance=SysCreditAccount.balance - normalized_cost,
                total_consumed=SysCreditAccount.total_consumed + normalized_cost,
                updated_at=_now_str(),
            )
        )
        result = await self.db.execute(stmt)

        if result.rowcount == 0:
            # 余额不足
            account = await self._get_account(user_id)
            balance_before = account.balance if account else 0
            raise ValueError(
                f"Insufficient credits: user={user_id}, feature={_code}, "
                f"cost={normalized_cost}, balance={balance_before}"
            )

        # 获取更新后的账户
        account_after = await self._get_account(user_id)
        balance_after = account_after.balance if account_after else 0
        balance_before = balance_after + normalized_cost

        # 记录交易
        transaction_type = "CONSUME" if normalized_cost > 0 else "USAGE"
        txn_id = await self._record_transaction(
            user_id=user_id,
            feature_code=_code,
            transaction_type=transaction_type,
            amount_delta=-normalized_cost,
            balance_before=balance_before,
            balance_after=balance_after,
            run_id=run_id,
            task_id=task_id,
            workflow_id=workflow_id,
            reason=reason,
        )
        await self.db.commit()

        return {
            "charged": True,
            "userId": user_id,
            "featureCode": _code,
            "cost": normalized_cost,
            "balanceBefore": balance_before,
            "balanceAfter": balance_after,
            "transactionId": txn_id,
        }

    async def refund(
        self, user_id: int, feature_code: str, amount: int,
        run_id: str = "", task_id: str = "", workflow_id: str = "", reason: str = "",
    ) -> bool:
        """退还用户积分。"""
        normalized_amount = max(0, amount)
        if user_id is None or normalized_amount <= 0:
            return False

        await self._ensure_account_balance(user_id, DEFAULT_INITIAL_BALANCE)

        account = await self._get_account(user_id)
        balance_before = account.balance if account else 0
        balance_after = balance_before + normalized_amount

        await self.db.execute(
            sa_update(SysCreditAccount)
            .where(SysCreditAccount.user_id == user_id)
            .values(balance=balance_after, updated_at=_now_str())
        )

        await self._record_transaction(
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
        await self.db.commit()
        return True

    async def adjust(self, user_id: int, amount: int, reason: str) -> Optional[dict]:
        """管理员调整用户积分。"""
        if amount == 0:
            raise ValueError("调整积分不能为 0")
        if not reason.strip():
            raise ValueError("调整原因不能为空")

        # 检查用户
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("user_not_found")
        if _is_admin_username(user.username):
            raise ValueError("admin 账号不参与积分调整")

        await self._ensure_account_balance(user_id, DEFAULT_INITIAL_BALANCE)

        account = await self._get_account(user_id)
        balance_before = account.balance if account else 0
        balance_after = balance_before + amount

        if balance_after < 0:
            raise ValueError("调整后积分不能小于 0")

        total_adjusted = (account.total_adjusted if account else 0) + amount

        await self.db.execute(
            sa_update(SysCreditAccount)
            .where(SysCreditAccount.user_id == user_id)
            .values(
                balance=balance_after,
                total_adjusted=total_adjusted,
                updated_at=_now_str(),
            )
        )

        await self._record_transaction(
            user_id=user_id,
            feature_code="",
            transaction_type="ADJUST",
            amount_delta=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason.strip(),
        )
        await self.db.commit()

        # 返回更新后的用户积分信息
        users = await self.list_users("", only_ids={user_id})
        return users[0] if users else None

    # ── 用户列表 ──────────────────────────────────────────────────

    async def list_users(self, q: str = "", only_ids: set[int] | None = None) -> list[dict]:
        """列出所有非 admin 用户的积分信息。"""
        stmt = select(SysUser).where(SysUser.username != "admin")

        keyword = q.strip().lower() if q else ""
        if keyword:
            stmt = stmt.where(
                SysUser.username.like(f"%{keyword}%")
                | SysUser.display_name.like(f"%{keyword}%")
            )

        if only_ids:
            stmt = stmt.where(SysUser.id.in_(only_ids))

        stmt = stmt.order_by(SysUser.created_at.desc())
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        # 确保所有活跃用户有积分账户
        for user in users:
            await self._ensure_account_balance(user.id, DEFAULT_INITIAL_BALANCE)
        await self.db.commit()

        if not users:
            return []

        user_ids = [u.id for u in users]
        accounts = await self._account_map(user_ids)
        usage_stats = await self._usage_stats(user_ids)

        return [
            self._to_credit_user_dict(
                user, accounts.get(user.id), usage_stats.get(user.id)
            )
            for user in users
        ]

    # ── 内部方法 ──────────────────────────────────────────────────

    async def _get_account(self, user_id: int) -> SysCreditAccount | None:
        result = await self.db.execute(
            select(SysCreditAccount).where(SysCreditAccount.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def _account_balance(self, user_id: int) -> dict:
        account = await self._get_account(user_id)
        if not account:
            return {"balance": 0, "totalConsumed": 0, "totalAdjusted": 0}
        return {
            "balance": account.balance or 0,
            "totalConsumed": account.total_consumed or 0,
            "totalAdjusted": account.total_adjusted or 0,
        }

    async def _rule_cost(self, feature_code: str) -> int:
        _code = normalize_feature_code(feature_code)
        if not _code:
            return 0
        result = await self.db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == _code).limit(1)
        )
        rule = result.scalar_one_or_none()
        return max(0, rule.cost) if rule and rule.cost else 0

    async def _ensure_account_balance(self, user_id: int, initial_balance: int):
        """如果账户不存在则创建。"""
        account = await self._get_account(user_id)
        if account:
            return
        now = _now_str()
        account = SysCreditAccount(
            user_id=user_id,
            balance=max(0, initial_balance),
            total_consumed=0,
            total_adjusted=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(account)
        await self.db.flush()

    async def _record_transaction(
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
        txn_id = "credit_" + uuid.uuid4().hex
        now = _now_str()
        txn = SysCreditTransaction(
            transaction_id=txn_id,
            user_id=user_id,
            feature_code=normalize_feature_code(feature_code),
            transaction_type=transaction_type,
            amount_delta=amount_delta,
            balance_before=balance_before,
            balance_after=balance_after,
            related_run_id=_trim(run_id),
            related_task_id=_trim(task_id),
            related_workflow_id=_trim(workflow_id),
            reason=_trim(reason),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=now,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn_id

    async def _account_map(self, user_ids: list[int]) -> dict[int, SysCreditAccount]:
        if not user_ids:
            return {}
        result = await self.db.execute(
            select(SysCreditAccount).where(SysCreditAccount.user_id.in_(user_ids))
        )
        return {a.user_id: a for a in result.scalars().all()}

    async def _usage_stats(self, user_ids: list[int]) -> dict[int, dict]:
        """统计各用户的图片/视频生成次数及最后使用时间。"""
        if not user_ids:
            return {}
        result = await self.db.execute(
            select(SysCreditTransaction)
            .where(
                SysCreditTransaction.user_id.in_(user_ids),
                SysCreditTransaction.transaction_type.in_(["CONSUME", "USAGE"]),
            )
            .order_by(SysCreditTransaction.created_at.asc())
        )
        stats_map: dict[int, dict] = {}
        for txn in result.scalars().all():
            uid = txn.user_id
            if uid not in stats_map:
                stats_map[uid] = {
                    "imageGenerationCount": 0,
                    "videoGenerationCount": 0,
                    "lastUsedAt": None,
                }
            fc = normalize_feature_code(txn.feature_code or "")
            if fc == IMAGE_GENERATION:
                stats_map[uid]["imageGenerationCount"] += 1
            if fc == VIDEO_GENERATION:
                stats_map[uid]["videoGenerationCount"] += 1
            if txn.created_at:
                if stats_map[uid]["lastUsedAt"] is None or txn.created_at > stats_map[uid]["lastUsedAt"]:
                    stats_map[uid]["lastUsedAt"] = txn.created_at
        return stats_map

    @staticmethod
    def _default_rule_name(feature_code: str) -> str:
        return {
            IMAGE_GENERATION: "图片生成",
            VIDEO_GENERATION: "视频生成",
        }.get(normalize_feature_code(feature_code), feature_code)

    @staticmethod
    def _account_to_dict(account: SysCreditAccount) -> dict:
        return {
            "id": account.id,
            "userId": account.user_id,
            "balance": account.balance or 0,
            "totalConsumed": account.total_consumed or 0,
            "totalAdjusted": account.total_adjusted or 0,
        }

    @staticmethod
    def _rule_to_dict(rule: SysCreditRule) -> dict:
        return {
            "featureCode": rule.feature_code,
            "displayName": rule.display_name,
            "cost": rule.cost or 0,
            "updatedAt": rule.updated_at,
        }

    @staticmethod
    def _transaction_to_dict(txn: SysCreditTransaction) -> dict:
        md = {}
        if txn.metadata_json:
            try:
                md = json.loads(txn.metadata_json)
            except (json.JSONDecodeError, TypeError):
                md = {}
        return {
            "transactionId": txn.transaction_id,
            "userId": txn.user_id,
            "featureCode": txn.feature_code,
            "transactionType": txn.transaction_type,
            "amountDelta": txn.amount_delta or 0,
            "balanceBefore": txn.balance_before or 0,
            "balanceAfter": txn.balance_after or 0,
            "relatedRunId": txn.related_run_id,
            "relatedTaskId": txn.related_task_id,
            "relatedWorkflowId": txn.related_workflow_id,
            "reason": txn.reason,
            "metadata": md,
            "createdAt": txn.created_at,
        }

    @staticmethod
    def _to_credit_user_dict(
        user: SysUser,
        account: SysCreditAccount | None,
        stats: dict | None,
    ) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name,
            "role": user.role,
            "status": user.status,
            "balance": account.balance if account else 0,
            "totalConsumed": account.total_consumed if account else 0,
            "totalAdjusted": account.total_adjusted if account else 0,
            "imageGenerationCount": stats["imageGenerationCount"] if stats else 0,
            "videoGenerationCount": stats["videoGenerationCount"] if stats else 0,
            "lastUsedAt": stats["lastUsedAt"] if stats else None,
        }
