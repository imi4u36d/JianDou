"""Credit rule catalog persistence and default-rule policy."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit import SysCreditRule
from backend.services.credit_presenters import rule_to_dict
from backend.shared import now_iso

IMAGE_GENERATION = "IMAGE_GENERATION"
VIDEO_GENERATION = "VIDEO_GENERATION"
DEFAULT_CREDIT_RULES = {
    IMAGE_GENERATION: ("图片生成", 10),
    VIDEO_GENERATION: ("视频生成", 50),
}


def normalize_feature_code(code: str) -> str:
    return code.strip().upper() if code else ""


class CreditRuleCatalog:
    """Read and mutate billable feature costs."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_rules(self) -> list[dict]:
        await self.ensure_defaults()
        result = await self._db.execute(
            select(SysCreditRule).order_by(SysCreditRule.feature_code.asc())
        )
        return [rule_to_dict(rule) for rule in result.scalars().all()]

    async def update_rule(self, feature_code: str, cost: int) -> dict | None:
        if cost < 0:
            raise ValueError("积分消耗值必须为非负整数")
        code = normalize_feature_code(feature_code)
        if not code:
            raise ValueError("功能编码不能为空")
        result = await self._db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == code).limit(1)
        )
        existing = result.scalar_one_or_none()
        now = now_iso()
        if existing:
            await self._db.execute(
                sa_update(SysCreditRule)
                .where(SysCreditRule.feature_code == code)
                .values(cost=max(0, cost), updated_at=now)
            )
        else:
            self._db.add(
                SysCreditRule(
                    feature_code=code,
                    display_name=self.default_rule_name(code),
                    cost=max(0, cost),
                    created_at=now,
                    updated_at=now,
                )
            )
        await self._db.commit()
        result = await self._db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == code).limit(1)
        )
        updated = result.scalar_one_or_none()
        return rule_to_dict(updated) if updated else None

    async def rule_cost(self, feature_code: str) -> int:
        code = normalize_feature_code(feature_code)
        if not code:
            return 0
        result = await self._db.execute(
            select(SysCreditRule).where(SysCreditRule.feature_code == code).limit(1)
        )
        rule = result.scalar_one_or_none()
        if rule:
            return max(0, rule.cost or 0)
        default = DEFAULT_CREDIT_RULES.get(code)
        return default[1] if default else 0

    async def ensure_defaults(self) -> None:
        result = await self._db.execute(
            select(SysCreditRule).where(
                SysCreditRule.feature_code.in_(DEFAULT_CREDIT_RULES.keys())
            )
        )
        existing = {
            normalize_feature_code(rule.feature_code) for rule in result.scalars().all()
        }
        missing = set(DEFAULT_CREDIT_RULES) - existing
        if not missing:
            return
        now = now_iso()
        for code in sorted(missing):
            display_name, cost = DEFAULT_CREDIT_RULES[code]
            self._db.add(
                SysCreditRule(
                    feature_code=code,
                    display_name=display_name,
                    cost=cost,
                    created_at=now,
                    updated_at=now,
                )
            )
        await self._db.commit()

    @staticmethod
    def default_rule_name(feature_code: str) -> str:
        return {
            code: display_name for code, (display_name, _cost) in DEFAULT_CREDIT_RULES.items()
        }.get(normalize_feature_code(feature_code), feature_code)
