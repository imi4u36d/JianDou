from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, Integer, String

from backend.database import Base


class SysUser(Base):
    __tablename__ = "sys_user"
    __table_args__ = (
        CheckConstraint("role in ('USER', 'ADMIN')", name="ck_sys_user_role"),
        CheckConstraint("status in ('ACTIVE', 'DISABLED')", name="ck_sys_user_status"),
        CheckConstraint("task_concurrency_limit between 1 and 20", name="ck_sys_user_task_concurrency_limit"),
        Index("ix_sys_user_role_status", "role", "status"),
        {"comment": "Application user account and authorization role."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    username = Column(String(64), nullable=False, unique=True, comment="Unique normalized login name.")
    password_hash = Column(String(255), nullable=False, comment="Password hash; never stores raw passwords.")
    role = Column(String(16), nullable=False, default="USER", comment="UserRole enum value: USER or ADMIN.")
    status = Column(String(16), nullable=False, default="ACTIVE", comment="UserStatus enum value: ACTIVE or DISABLED.")
    last_login_at = Column(String(32), nullable=True, comment="ISO timestamp of the latest successful login.")
    task_concurrency_limit = Column(Integer, nullable=False, default=1, comment="Maximum concurrent tasks allowed for the user.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the account was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the account was last updated.")


class SysUserPreference(Base):
    __tablename__ = "sys_user_preference"
    __table_args__ = (
        Index("ux_sys_user_preference_user_key", "user_id", "preference_key", unique=True),
        Index("ix_sys_user_preference_user", "user_id"),
        {"comment": "Per-user durable preference key-value storage."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    user_id = Column(Integer, nullable=False, comment="Owner sys_user.id.")
    preference_key = Column(String(128), nullable=False, comment="Stable preference key, e.g. generation.default_aspect_ratio.")
    preference_value = Column(String(2048), nullable=False, comment="Serialized preference value.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the preference was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the preference was last updated.")


class SysUserModelCredential(Base):
    __tablename__ = "sys_user_model_credential"
    __table_args__ = (
        Index("ux_sys_user_model_credential_user_provider", "user_id", "provider_key", unique=True),
        {"comment": "Per-user encrypted model provider credentials."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    user_id = Column(Integer, nullable=False, comment="Owner sys_user.id.")
    provider_key = Column(String(64), nullable=False, comment="Normalized model provider key.")
    encrypted_api_key = Column(String(255), nullable=False, comment="Encrypted or locally protected API key value.")
    base_url = Column(String(1024), nullable=False, default="", comment="User-scoped provider API base URL.")
    task_base_url = Column(String(1024), nullable=False, default="", comment="User-scoped async task polling base URL.")
    extras_json = Column(String(2048), nullable=False, default="{}", comment="User-scoped provider runtime extras JSON.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the credential was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the credential was last updated.")


class SysInviteCode(Base):
    __tablename__ = "sys_invite_code"
    __table_args__ = (
        CheckConstraint("role in ('USER', 'ADMIN')", name="ck_sys_invite_code_role"),
        CheckConstraint("status in ('UNUSED', 'USED', 'EXPIRED', 'REVOKED')", name="ck_sys_invite_code_status"),
        Index("ix_sys_invite_code_status", "status"),
        {"comment": "Invite codes used to activate user or admin accounts."},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Internal numeric primary key.")
    code = Column(String(64), nullable=False, unique=True, comment="Unique invite code presented to new users.")
    role = Column(String(16), nullable=False, default="USER", comment="Role assigned to the activated user.")
    status = Column(String(16), nullable=False, default="UNUSED", comment="InviteStatus enum value.")
    expires_at = Column(String(32), nullable=True, comment="Optional ISO expiry timestamp.")
    created_by = Column(Integer, nullable=True, comment="Admin sys_user.id that created the invite.")
    used_by = Column(Integer, nullable=True, comment="sys_user.id created through this invite.")
    used_at = Column(String(32), nullable=True, comment="ISO timestamp when the invite was used.")
    created_at = Column(String(32), nullable=False, comment="ISO timestamp when the invite was created.")
    updated_at = Column(String(32), nullable=False, comment="ISO timestamp when the invite was last updated.")
