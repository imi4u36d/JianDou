from __future__ import annotations

from sqlalchemy import Column, Integer, String

from backend.database import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(128), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="USER")
    status = Column(String(16), nullable=False, default="ACTIVE")
    last_login_at = Column(String(32), nullable=True)
    task_concurrency_limit = Column(Integer, nullable=False, default=1)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)


class SysUserModelCredential(Base):
    __tablename__ = "sys_user_model_credential"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    provider_key = Column(String(64), nullable=False)
    encrypted_api_key = Column(String(255), nullable=False)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)


class SysInviteCode(Base):
    __tablename__ = "sys_invite_code"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True)
    role = Column(String(16), nullable=False, default="USER")
    status = Column(String(16), nullable=False, default="ACTIVE")
    expires_at = Column(String(32), nullable=True)
    created_by = Column(Integer, nullable=True)
    used_by = Column(Integer, nullable=True)
    used_at = Column(String(32), nullable=True)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)
