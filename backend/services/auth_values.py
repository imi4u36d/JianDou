"""Pure authentication input validation and enum normalization."""

from __future__ import annotations

import re

from backend.domain.enums import InviteStatus, UserRole, UserStatus

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


def normalize_username(username: str) -> str:
    return username.strip().lower() if username else ""


def normalize_invite_code(code: str) -> str:
    return code.strip().upper() if code else ""


def validate_username(username: str) -> str:
    normalized = normalize_username(username)
    if not USERNAME_PATTERN.match(normalized):
        raise ValueError("用户名需为 3 到 32 位，仅支持字母、数字、点、下划线和中划线")
    return normalized


def validate_password(password: str) -> str:
    normalized = password.strip() if password else ""
    if len(normalized) < 8 or len(normalized.encode("utf-8")) > 72:
        raise ValueError("密码长度需至少 8 个字符，且 UTF-8 编码不超过 72 字节")
    return normalized


def validate_invite_code(code: str) -> str:
    normalized = normalize_invite_code(code)
    if not normalized:
        raise ValueError("邀请码不能为空")
    return normalized


def normalize_user_role(role: str | UserRole | None) -> str:
    raw = role.value if isinstance(role, UserRole) else str(role or UserRole.USER.value).strip().upper()
    try:
        return UserRole(raw).value
    except ValueError as exc:
        raise ValueError("invalid_user_role") from exc


def normalize_user_status(status: str | UserStatus | None) -> str:
    raw = status.value if isinstance(status, UserStatus) else str(status or UserStatus.ACTIVE.value).strip().upper()
    try:
        return UserStatus(raw).value
    except ValueError as exc:
        raise ValueError("invalid_user_status") from exc


def normalize_invite_status(status: str | InviteStatus | None) -> str:
    raw = status.value if isinstance(status, InviteStatus) else str(status or InviteStatus.UNUSED.value).strip().upper()
    try:
        return InviteStatus(raw).value
    except ValueError as exc:
        raise ValueError("invalid_invite_status") from exc
