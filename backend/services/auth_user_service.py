"""Authentication sessions and administrative user lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import hash_password, verify_password
from backend.domain.enums import UserRole, UserStatus
from backend.models.user import SysUser
from backend.services.auth_presenters import admin_user_to_dict, user_to_dict
from backend.services.auth_values import (
    normalize_user_role,
    normalize_user_status,
    normalize_username,
    validate_password,
    validate_username,
)


def _now_str() -> str:
    return datetime.now(UTC).isoformat()


class AuthUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, username: str, password: str) -> dict | None:
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == normalize_username(username))
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None
        if user.status != UserStatus.ACTIVE.value:
            raise ValueError("account_disabled")
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user.id).values(last_login_at=_now_str())
        )
        await self.db.commit()
        return user_to_dict(user)

    async def get_session_user(self, user_id: int) -> dict | None:
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE.value:
            return None
        return user_to_dict(user)

    async def get_user_by_id(self, user_id: int) -> dict | None:
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        return user_to_dict(user) if user else None

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = UserRole.USER.value,
        status: str = UserStatus.ACTIVE.value,
        task_concurrency_limit: int = 1,
    ) -> dict:
        normalized_username = validate_username(username)
        normalized_password = validate_password(password)
        normalized_role = normalize_user_role(role)
        normalized_status = normalize_user_status(status)
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == normalized_username)
        )
        if result.scalar_one_or_none():
            raise ValueError("username_taken")
        now = _now_str()
        user = SysUser(
            username=normalized_username,
            password_hash=hash_password(normalized_password),
            role=normalized_role,
            status=normalized_status,
            task_concurrency_limit=max(1, min(20, task_concurrency_limit)),
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user_to_dict(user)

    async def list_users(
        self,
        q: str = "",
        role: str = "",
        status: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        keyword = q.strip().lower() if q else ""
        normalized_role = normalize_user_role(role) if role else ""
        normalized_status = normalize_user_status(status) if status else ""
        conditions = []
        if keyword:
            conditions.append(SysUser.username.like(f"%{keyword}%"))
        if normalized_role:
            conditions.append(SysUser.role == normalized_role)
        if normalized_status:
            conditions.append(SysUser.status == normalized_status)
        where_clause = and_(*conditions) if conditions else None

        count_stmt = select(func.count()).select_from(SysUser)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = select(SysUser)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        stmt = stmt.order_by(
            SysUser.role.asc(),
            SysUser.status.asc(),
            SysUser.created_at.desc(),
        ).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return {
            "items": [admin_user_to_dict(user) for user in result.scalars().all()],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def update_user(self, user_id: int, updates: dict) -> dict | None:
        existing = await self._require_user(user_id)
        role = normalize_user_role(updates["role"]) if updates.get("role") is not None else None
        status = normalize_user_status(updates["status"]) if updates.get("status") is not None else None
        concurrency = updates.get("task_concurrency_limit")
        if role is not None or status is not None:
            await self._check_admin_guard(
                existing,
                role or existing["role"],
                status or existing["status"],
            )
        values = {}
        if role is not None:
            values["role"] = role
        if status is not None:
            values["status"] = status
        if concurrency is not None:
            values["task_concurrency_limit"] = max(1, min(20, int(concurrency)))
        if not values:
            return existing
        values["updated_at"] = _now_str()
        await self.db.execute(sa_update(SysUser).where(SysUser.id == user_id).values(**values))
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: int) -> bool:
        existing = await self._require_user(user_id)
        await self._check_admin_guard(
            existing,
            UserRole.USER.value,
            UserStatus.DISABLED.value,
        )
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(status=UserStatus.DISABLED.value)
        )
        await self.db.commit()
        return True

    async def enable_user(self, user_id: int) -> dict | None:
        await self._require_user(user_id)
        await self._set_user_status(user_id, UserStatus.ACTIVE.value)
        return await self.get_user_by_id(user_id)

    async def disable_user(self, user_id: int) -> dict | None:
        existing = await self._require_user(user_id)
        if existing["status"] == UserStatus.DISABLED.value:
            return existing
        await self._check_admin_guard(existing, existing["role"], UserStatus.DISABLED.value)
        await self._set_user_status(user_id, UserStatus.DISABLED.value)
        return await self.get_user_by_id(user_id)

    async def update_password(self, user_id: int, password: str) -> dict | None:
        await self._require_user(user_id)
        password_hash = hash_password(validate_password(password))
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(
                password_hash=password_hash,
                updated_at=_now_str(),
            )
        )
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def _set_user_status(self, user_id: int, status: str) -> None:
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(
                status=status,
                updated_at=_now_str(),
            )
        )
        await self.db.commit()

    async def _require_user(self, user_id: int) -> dict:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")
        return user

    async def _check_admin_guard(
        self,
        existing: dict,
        next_role: str,
        next_status: str,
    ) -> None:
        current_admin = existing["role"] == UserRole.ADMIN.value
        current_active_admin = current_admin and existing["status"] == UserStatus.ACTIVE.value
        next_admin = next_role == UserRole.ADMIN.value
        next_active_admin = next_admin and next_status == UserStatus.ACTIVE.value
        if current_admin and not next_admin:
            count = await self._admin_count(active_only=False)
            if count <= 1:
                raise ValueError("last_admin_guard")
        if current_active_admin and not next_active_admin:
            count = await self._admin_count(active_only=True)
            if count <= 1:
                raise ValueError("last_active_admin_guard")

    async def _admin_count(self, active_only: bool) -> int:
        stmt = select(func.count()).select_from(SysUser).where(SysUser.role == UserRole.ADMIN.value)
        if active_only:
            stmt = stmt.where(SysUser.status == UserStatus.ACTIVE.value)
        return (await self.db.execute(stmt)).scalar() or 0
