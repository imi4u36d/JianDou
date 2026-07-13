"""Invite-code lifecycle for authentication and administration."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import hash_password
from backend.domain.enums import InviteStatus, UserStatus
from backend.models.user import SysInviteCode, SysUser

INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now_str() -> str:
    return datetime.now(UTC).isoformat()


def _generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(12))


class AuthInviteService:
    def __init__(
        self,
        db: AsyncSession,
        normalize_role: Callable[[str], str],
        validate_code: Callable[[str], str],
        validate_username: Callable[[str], str],
        validate_password: Callable[[str], str],
        user_to_dict: Callable[[SysUser], dict],
    ) -> None:
        self._db = db
        self._normalize_role = normalize_role
        self._validate_code = validate_code
        self._validate_username = validate_username
        self._validate_password = validate_password
        self._user_to_dict = user_to_dict

    async def create_invite(self, role: str, created_by: int, expires_at: str | None = None) -> dict:
        normalized_role = self._normalize_role(role)
        normalized_expires_at = expires_at.strip() if isinstance(expires_at, str) and expires_at.strip() else None
        for _attempt in range(10):
            code = _generate_invite_code()
            result = await self._db.execute(select(SysInviteCode).where(SysInviteCode.code == code))
            if result.scalar_one_or_none() is None:
                break
        else:
            raise RuntimeError("invite_generation_failed")

        now = _now_str()
        invite = SysInviteCode(
            code=code,
            role=normalized_role,
            status=InviteStatus.UNUSED.value,
            expires_at=normalized_expires_at,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._db.add(invite)
        await self._db.commit()
        await self._db.refresh(invite)
        return self.to_invite_dict(invite)

    async def list_invites(self) -> list[dict]:
        await self._expire_invites()
        result = await self._db.execute(select(SysInviteCode).order_by(SysInviteCode.created_at.desc()))
        invites = result.scalars().all()
        user_ids = {
            user_id
            for invite in invites
            for user_id in (invite.created_by, invite.used_by)
            if user_id
        }
        user_map: dict[int, dict] = {}
        if user_ids:
            result = await self._db.execute(select(SysUser).where(SysUser.id.in_(user_ids)))
            user_map = {user.id: self._user_to_dict(user) for user in result.scalars().all()}
        rows = []
        for invite in invites:
            row = self.to_invite_dict(invite)
            row["created_by_user"] = user_map.get(invite.created_by)
            row["used_by_user"] = user_map.get(invite.used_by)
            rows.append(row)
        return rows

    async def revoke_invite(self, invite_id: int) -> dict | None:
        result = await self._db.execute(select(SysInviteCode).where(SysInviteCode.id == invite_id))
        invite = result.scalar_one_or_none()
        if not invite:
            raise ValueError("invite_not_found")
        invite = await self._normalize_invite_status(invite)
        if invite.status == InviteStatus.USED.value:
            raise ValueError("invite_already_used")
        if invite.status != InviteStatus.REVOKED.value:
            await self._db.execute(
                sa_update(SysInviteCode)
                .where(SysInviteCode.id == invite_id)
                .values(status=InviteStatus.REVOKED.value, updated_at=_now_str())
            )
            await self._db.commit()
        result = await self._db.execute(select(SysInviteCode).where(SysInviteCode.id == invite_id))
        updated = result.scalar_one_or_none()
        return self.to_invite_dict(updated) if updated else None

    async def activate_invite(self, code: str, username: str, password: str) -> dict | None:
        normalized_code = self._validate_code(code)
        normalized_username = self._validate_username(username)
        normalized_password = self._validate_password(password)
        result = await self._db.execute(select(SysInviteCode).where(SysInviteCode.code == normalized_code))
        invite = result.scalar_one_or_none()
        if not invite:
            raise ValueError("invite_not_found")
        invite = await self._normalize_invite_status(invite)
        if invite.status != InviteStatus.UNUSED.value:
            raise ValueError(self.activate_error_message(invite.status))
        result = await self._db.execute(select(SysUser).where(SysUser.username == normalized_username))
        if result.scalar_one_or_none():
            raise ValueError("username_taken")

        now = _now_str()
        user = SysUser(
            username=normalized_username,
            password_hash=hash_password(normalized_password),
            role=invite.role,
            status=UserStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.execute(
            sa_update(SysInviteCode)
            .where(SysInviteCode.id == invite.id)
            .values(status=InviteStatus.USED.value, used_by=user.id, used_at=now, updated_at=now)
        )
        await self._db.commit()
        await self._db.refresh(user)
        return self._user_to_dict(user)

    async def _expire_invites(self) -> None:
        now = datetime.now(UTC)
        result = await self._db.execute(
            select(SysInviteCode).where(
                SysInviteCode.status == InviteStatus.UNUSED.value,
                SysInviteCode.expires_at.isnot(None),
            )
        )
        for invite in result.scalars().all():
            if invite.expires_at:
                try:
                    if datetime.fromisoformat(invite.expires_at) <= now:
                        await self._db.execute(
                            sa_update(SysInviteCode)
                            .where(SysInviteCode.id == invite.id)
                            .values(status=InviteStatus.EXPIRED.value)
                        )
                except (ValueError, TypeError):
                    pass
        await self._db.commit()

    async def _normalize_invite_status(self, invite: SysInviteCode) -> SysInviteCode:
        if invite.status == InviteStatus.UNUSED.value and invite.expires_at:
            try:
                if datetime.fromisoformat(invite.expires_at) <= datetime.now(UTC):
                    await self._db.execute(
                        sa_update(SysInviteCode)
                        .where(SysInviteCode.id == invite.id)
                        .values(status=InviteStatus.EXPIRED.value, updated_at=_now_str())
                    )
                    await self._db.commit()
                    invite.status = InviteStatus.EXPIRED.value
            except (ValueError, TypeError):
                pass
        return invite

    @staticmethod
    def activate_error_message(status: str) -> str:
        return {
            InviteStatus.USED.value: "invite_already_used",
            InviteStatus.REVOKED.value: "invite_revoked",
            InviteStatus.EXPIRED.value: "invite_expired",
        }.get(status, "invite_invalid")

    @staticmethod
    def to_invite_dict(invite: SysInviteCode) -> dict:
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
