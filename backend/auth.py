from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings
from backend.domain.enums import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def normalize_role(role: str | UserRole | None) -> str:
    if isinstance(role, UserRole):
        return role.value
    raw = str(role or UserRole.USER.value).strip().upper()
    try:
        return UserRole(raw).value
    except ValueError:
        return UserRole.USER.value


def create_token_data(user_id: int, username: str, role: str | UserRole) -> dict:
    return {
        "sub": str(user_id),
        "username": username,
        "role": normalize_role(role),
    }


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def delete_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        secure=settings.cookie_secure,
        samesite="lax",
    )


async def get_current_user(request: Request) -> Optional[dict]:
    """Resolve the current active user from the JWT cookie and database."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    try:
        user_id = int(payload.get("sub", "0"))
    except (TypeError, ValueError):
        return None
    if user_id <= 0:
        return None

    from sqlalchemy import select

    import backend.database as database
    from backend.models.user import SysUser

    async with database.async_session_factory() as session:
        result = await session.execute(select(SysUser).where(SysUser.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.status != "ACTIVE":
            return None

    return {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name,
        "role": normalize_role(user.role),
        "status": user.status,
    }


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def require_admin(request: Request) -> dict:
    user = await require_user(request)
    if user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
