from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import hash_password, verify_password
from backend.models.user import SysInviteCode, SysUser

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize_username(username: str) -> str:
    return username.strip().lower() if username else ""


def normalize_invite_code(code: str) -> str:
    return code.strip().upper() if code else ""


def validate_username(username: str) -> str:
    normalized = normalize_username(username)
    if not USERNAME_PATTERN.match(normalized):
        raise ValueError("用户名需为 3 到 32 位，仅支持字母、数字、点、下划线和中划线")
    return normalized


def validate_display_name(display_name: str) -> str:
    normalized = display_name.strip() if display_name else ""
    if not normalized:
        raise ValueError("显示名不能为空")
    if len(normalized) > 128:
        raise ValueError("显示名长度不能超过 128 个字符")
    return normalized


def validate_password(password: str) -> str:
    normalized = password.strip() if password else ""
    if len(normalized) < 8 or len(normalized) > 72:
        raise ValueError("密码长度需在 8 到 72 个字符之间")
    return normalized


def validate_invite_code(code: str) -> str:
    normalized = normalize_invite_code(code)
    if not normalized:
        raise ValueError("邀请码不能为空")
    return normalized


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_invite_code() -> str:
    return "".join(__import__("random").choice(INVITE_CODE_ALPHABET) for _ in range(12))


class AuthService:
    """认证服务 —— 用户登录、会话、管理端用户与邀请码 CRUD。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 会话 / 登录 ──────────────────────────────────────────────

    async def login(self, username: str, password: str) -> Optional[dict]:
        """验证用户名密码，返回用户 dict 或 None。"""
        normalized = normalize_username(username)
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == normalized)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if user.status != "ACTIVE":
            raise ValueError("account_disabled")

        # 更新最后登录时间
        stmt = (
            sa_update(SysUser)
            .where(SysUser.id == user.id)
            .values(last_login_at=_now_str())
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return self._to_user_dict(user)

    async def get_session_user(self, user_id: int) -> Optional[dict]:
        """根据 ID 获取用户会话信息（含状态检查）。"""
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.status != "ACTIVE":
            return None
        return self._to_user_dict(user)

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据 ID 获取用户（不检查状态）。"""
        result = await self.db.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return self._to_user_dict(user)

    # ── 用户 CRUD ────────────────────────────────────────────────

    async def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        role: str = "USER",
        status: str = "ACTIVE",
        task_concurrency_limit: int = 1,
    ) -> dict:
        _username = validate_username(username)
        _display_name = validate_display_name(display_name)
        _password = validate_password(password)

        # 检查用户名是否已存在
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == _username)
        )
        if result.scalar_one_or_none():
            raise ValueError("username_taken")

        now = _now_str()
        pwd_hash = hash_password(_password)
        user = SysUser(
            username=_username,
            display_name=_display_name,
            password_hash=pwd_hash,
            role=role,
            status=status,
            task_concurrency_limit=max(1, min(20, task_concurrency_limit)),
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return self._to_user_dict(user)

    async def list_users(
        self, q: str = "", role: str = "", status: str = ""
    ) -> list[dict]:
        stmt = select(SysUser)
        keyword = q.strip().lower() if q else ""
        _role = role.strip().upper() if role else ""
        _status = status.strip().upper() if status else ""

        conditions = []
        if keyword:
            conditions.append(
                SysUser.username.like(f"%{keyword}%")
                | SysUser.display_name.like(f"%{keyword}%")
            )
        if _role:
            conditions.append(SysUser.role == _role)
        if _status:
            conditions.append(SysUser.status == _status)

        if conditions:
            from sqlalchemy import and_
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(SysUser.role.asc(), SysUser.status.asc(), SysUser.created_at.desc())
        result = await self.db.execute(stmt)
        return [self._to_admin_user_dict(u) for u in result.scalars().all()]

    async def update_user(self, user_id: int, updates: dict) -> Optional[dict]:
        existing = await self._require_user(user_id)

        display_name = updates.get("display_name")
        role = updates.get("role")
        status = updates.get("status")
        task_concurrency_limit = updates.get("task_concurrency_limit")

        if display_name is not None:
            validate_display_name(display_name)

        # Admin guard
        if role is not None or status is not None:
            await self._check_admin_guard(
                existing,
                role or existing["role"],
                status or existing["status"],
            )

        values = {}
        if display_name is not None:
            values["display_name"] = display_name
        if role is not None:
            values["role"] = role
        if status is not None:
            values["status"] = status
        if task_concurrency_limit is not None:
            limit = max(1, min(20, int(task_concurrency_limit)))
            values["task_concurrency_limit"] = limit

        if not values:
            return existing

        values["updated_at"] = _now_str()
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(**values)
        )
        await self.db.commit()

        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: int) -> bool:
        existing = await self._require_user(user_id)
        await self._check_admin_guard(existing, "USER", "DISABLED")
        await self.db.execute(sa_update(SysUser).where(SysUser.id == user_id).values(status="DELETED"))
        await self.db.commit()
        return True

    async def enable_user(self, user_id: int) -> Optional[dict]:
        await self._require_user(user_id)
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(
                status="ACTIVE", updated_at=_now_str()
            )
        )
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def disable_user(self, user_id: int) -> Optional[dict]:
        existing = await self._require_user(user_id)
        if existing["status"] == "DISABLED":
            return existing
        await self._check_admin_guard(existing, existing["role"], "DISABLED")
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(
                status="DISABLED", updated_at=_now_str()
            )
        )
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def update_password(self, user_id: int, password: str) -> Optional[dict]:
        await self._require_user(user_id)
        _password = validate_password(password)
        pwd_hash = hash_password(_password)
        await self.db.execute(
            sa_update(SysUser).where(SysUser.id == user_id).values(
                password_hash=pwd_hash, updated_at=_now_str()
            )
        )
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    # ── 邀请码 CRUD ──────────────────────────────────────────────

    async def create_invite(self, role: str, created_by: int) -> dict:
        from backend.config import settings

        role = role.upper()
        if role not in ("USER", "ADMIN"):
            raise ValueError("invalid_user_role")

        expires_at = _now_str()  # expires_at stored as ISO string

        # 尝试生成不重复的邀请码，最多 10 次
        for _attempt in range(10):
            code = _generate_invite_code()
            result = await self.db.execute(
                select(SysInviteCode).where(SysInviteCode.code == code)
            )
            if result.scalar_one_or_none() is None:
                break
        else:
            raise RuntimeError("invite_generation_failed")

        now = _now_str()
        invite = SysInviteCode(
            code=code,
            role=role,
            status="UNUSED",
            expires_at=expires_at,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return self._to_invite_dict(invite)

    async def list_invites(self) -> list[dict]:
        # 先过期未使用的邀请码
        await self._expire_invites()

        result = await self.db.execute(
            select(SysInviteCode).order_by(SysInviteCode.created_at.desc())
        )
        invites = result.scalars().all()

        # 收集关联的用户 ID
        user_ids = set()
        for invite in invites:
            if invite.created_by:
                user_ids.add(invite.created_by)
            if invite.used_by:
                user_ids.add(invite.used_by)

        user_map: dict[int, dict] = {}
        if user_ids:
            result = await self.db.execute(
                select(SysUser).where(SysUser.id.in_(user_ids))
            )
            for u in result.scalars().all():
                user_map[u.id] = self._to_user_dict(u)

        result_list = []
        for invite in invites:
            d = self._to_invite_dict(invite)
            d["created_by_user"] = user_map.get(invite.created_by)
            d["used_by_user"] = user_map.get(invite.used_by)
            result_list.append(d)
        return result_list

    async def revoke_invite(self, invite_id: int) -> Optional[dict]:
        result = await self.db.execute(
            select(SysInviteCode).where(SysInviteCode.id == invite_id)
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise ValueError("invite_not_found")

        # 过期检查
        invite = await self._normalize_invite_status(invite)
        if invite.status == "USED":
            raise ValueError("invite_already_used")
        if invite.status != "REVOKED":
            await self.db.execute(
                sa_update(SysInviteCode)
                .where(SysInviteCode.id == invite_id)
                .values(status="REVOKED", updated_at=_now_str())
            )
            await self.db.commit()

        result = await self.db.execute(
            select(SysInviteCode).where(SysInviteCode.id == invite_id)
        )
        updated_invite = result.scalar_one_or_none()
        return self._to_invite_dict(updated_invite) if updated_invite else None

    async def activate_invite(
        self, code: str, username: str, display_name: str, password: str
    ) -> Optional[dict]:
        _code = validate_invite_code(code)
        _username = validate_username(username)
        _display_name = validate_display_name(display_name)
        _password = validate_password(password)

        # 查找邀请码
        result = await self.db.execute(
            select(SysInviteCode).where(SysInviteCode.code == _code)
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise ValueError("invite_not_found")

        invite = await self._normalize_invite_status(invite)
        if invite.status != "UNUSED":
            raise ValueError(self._activate_error_message(invite.status))

        # 检查用户名是否已存在
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == _username)
        )
        if result.scalar_one_or_none():
            raise ValueError("username_taken")

        # 创建用户（自动提交事务）
        now = _now_str()
        pwd_hash = hash_password(_password)
        user = SysUser(
            username=_username,
            display_name=_display_name,
            password_hash=pwd_hash,
            role=invite.role,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        await self.db.flush()  # 获取 user.id

        # 更新邀请码
        await self.db.execute(
            sa_update(SysInviteCode)
            .where(SysInviteCode.id == invite.id)
            .values(status="USED", used_by=user.id, used_at=now, updated_at=now)
        )
        await self.db.commit()
        await self.db.refresh(user)
        return self._to_user_dict(user)

    # ── 内部辅助 ──────────────────────────────────────────────────

    async def _require_user(self, user_id: int) -> dict:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")
        return user

    async def _check_admin_guard(
        self, existing: dict, next_role: str, next_status: str
    ):
        """确保不会禁用/删除最后一个管理员。"""
        current_admin = existing["role"] == "ADMIN"
        current_active_admin = current_admin and existing["status"] == "ACTIVE"
        next_admin = next_role == "ADMIN"
        next_active_admin = next_admin and next_status == "ACTIVE"

        if current_admin and not next_admin:
            result = await self.db.execute(
                select(func.count()).select_from(SysUser).where(SysUser.role == "ADMIN")
            )
            admin_count = result.scalar() or 0
            if admin_count <= 1:
                raise ValueError("last_admin_guard")

        if current_active_admin and not next_active_admin:
            result = await self.db.execute(
                select(func.count()).select_from(SysUser).where(
                    SysUser.role == "ADMIN", SysUser.status == "ACTIVE"
                )
            )
            active_admin_count = result.scalar() or 0
            if active_admin_count <= 1:
                raise ValueError("last_active_admin_guard")

    async def _expire_invites(self):
        """过期所有已过期的未使用邀请码。"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(SysInviteCode).where(
                SysInviteCode.status == "UNUSED",
                SysInviteCode.expires_at.isnot(None),
            )
        )
        invites = result.scalars().all()
        for invite in invites:
            if invite.expires_at:
                try:
                    expires = datetime.fromisoformat(invite.expires_at)
                    if expires <= now:
                        await self.db.execute(
                            sa_update(SysInviteCode)
                            .where(SysInviteCode.id == invite.id)
                            .values(status="EXPIRED")
                        )
                except (ValueError, TypeError):
                    pass
        await self.db.commit()

    async def _normalize_invite_status(self, invite: SysInviteCode) -> SysInviteCode:
        """如果邀请码已过期但状态还是 UNUSED，将其标记为 EXPIRED。"""
        if invite.status == "UNUSED" and invite.expires_at:
            try:
                expires = datetime.fromisoformat(invite.expires_at)
                if expires <= datetime.now(timezone.utc):
                    await self.db.execute(
                        sa_update(SysInviteCode)
                        .where(SysInviteCode.id == invite.id)
                        .values(status="EXPIRED", updated_at=_now_str())
                    )
                    await self.db.commit()
                    invite.status = "EXPIRED"
            except (ValueError, TypeError):
                pass
        return invite

    @staticmethod
    def _activate_error_message(status: str) -> str:
        return {
            "USED": "invite_already_used",
            "REVOKED": "invite_revoked",
            "EXPIRED": "invite_expired",
        }.get(status, "invite_invalid")

    @staticmethod
    def _to_user_dict(user: SysUser) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name,
            "role": user.role,
            "status": user.status,
            "taskConcurrencyLimit": user.task_concurrency_limit,
            "lastLoginAt": user.last_login_at,
            "createdAt": user.created_at,
            "updatedAt": user.updated_at,
        }

    @staticmethod
    def _to_admin_user_dict(user: SysUser) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name,
            "role": user.role,
            "status": user.status,
            "taskConcurrencyLimit": user.task_concurrency_limit,
            "lastLoginAt": user.last_login_at,
            "createdAt": user.created_at,
            "updatedAt": user.updated_at,
        }

    @staticmethod
    def _to_invite_dict(invite: SysInviteCode) -> dict:
        return {
            "id": invite.id,
            "code": invite.code,
            "role": invite.role,
            "status": invite.status,
            "expiresAt": invite.expires_at,
            "createdBy": invite.created_by,
            "usedBy": invite.used_by,
            "usedAt": invite.used_at,
            "createdAt": invite.created_at,
            "updatedAt": invite.updated_at,
        }
