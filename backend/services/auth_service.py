"""Stable authentication facade for user and invite lifecycles."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.enums import UserRole, UserStatus
from backend.models.user import SysInviteCode, SysUser
from backend.services.auth_invite_service import AuthInviteService
from backend.services.auth_presenters import admin_user_to_dict, user_to_dict
from backend.services.auth_user_service import AuthUserService
from backend.services.auth_values import (
    normalize_invite_code,
    normalize_invite_status,
    normalize_user_role,
    normalize_user_status,
    normalize_username,
    validate_invite_code,
    validate_password,
    validate_username,
)

__all__ = [
    "AuthService",
    "normalize_invite_code",
    "normalize_invite_status",
    "normalize_user_role",
    "normalize_user_status",
    "normalize_username",
    "validate_invite_code",
    "validate_password",
    "validate_username",
]


class AuthService:
    """Compose user/session and invite services behind the established API."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._user_service = AuthUserService(db)
        self._invite_service = AuthInviteService(
            db,
            normalize_user_role,
            validate_invite_code,
            validate_username,
            validate_password,
            user_to_dict,
        )

    async def login(self, username: str, password: str) -> dict | None:
        return await self._user_service.login(username, password)

    async def get_session_user(self, user_id: int) -> dict | None:
        return await self._user_service.get_session_user(user_id)

    async def get_user_by_id(self, user_id: int) -> dict | None:
        return await self._user_service.get_user_by_id(user_id)

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = UserRole.USER.value,
        status: str = UserStatus.ACTIVE.value,
        task_concurrency_limit: int = 1,
    ) -> dict:
        return await self._user_service.create_user(
            username,
            password,
            role,
            status,
            task_concurrency_limit,
        )

    async def list_users(
        self,
        q: str = "",
        role: str = "",
        status: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        return await self._user_service.list_users(q, role, status, offset, limit)

    async def update_user(self, user_id: int, updates: dict) -> dict | None:
        return await self._user_service.update_user(user_id, updates)

    async def delete_user(self, user_id: int) -> bool:
        return await self._user_service.delete_user(user_id)

    async def enable_user(self, user_id: int) -> dict | None:
        return await self._user_service.enable_user(user_id)

    async def disable_user(self, user_id: int) -> dict | None:
        return await self._user_service.disable_user(user_id)

    async def update_password(self, user_id: int, password: str) -> dict | None:
        return await self._user_service.update_password(user_id, password)

    async def create_invite(
        self,
        role: str,
        created_by: int,
        expires_at: str | None = None,
    ) -> dict:
        return await self._invite_service.create_invite(role, created_by, expires_at)

    async def list_invites(self) -> list[dict]:
        return await self._invite_service.list_invites()

    async def revoke_invite(self, invite_id: int) -> dict | None:
        return await self._invite_service.revoke_invite(invite_id)

    async def activate_invite(self, code: str, username: str, password: str) -> dict | None:
        return await self._invite_service.activate_invite(code, username, password)

    async def _require_user(self, user_id: int) -> dict:
        return await self._user_service._require_user(user_id)

    async def _check_admin_guard(self, existing: dict, next_role: str, next_status: str) -> None:
        await self._user_service._check_admin_guard(existing, next_role, next_status)

    async def _expire_invites(self) -> None:
        await self._invite_service._expire_invites()

    async def _normalize_invite_status(self, invite: SysInviteCode) -> SysInviteCode:
        return await self._invite_service._normalize_invite_status(invite)

    @staticmethod
    def _activate_error_message(status: str) -> str:
        return AuthInviteService.activate_error_message(status)

    @staticmethod
    def _to_user_dict(user: SysUser) -> dict:
        return user_to_dict(user)

    @staticmethod
    def _to_admin_user_dict(user: SysUser) -> dict:
        return admin_user_to_dict(user)

    @staticmethod
    def _to_invite_dict(invite: SysInviteCode) -> dict:
        return AuthInviteService.to_invite_dict(invite)
