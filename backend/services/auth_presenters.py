"""Stable authentication response projections."""

from __future__ import annotations

from backend.models.user import SysUser


def user_to_dict(user: SysUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "status": user.status,
        "taskConcurrencyLimit": user.task_concurrency_limit,
        "lastLoginAt": user.last_login_at,
        "createdAt": user.created_at,
        "updatedAt": user.updated_at,
    }


def admin_user_to_dict(user: SysUser) -> dict:
    return user_to_dict(user)
