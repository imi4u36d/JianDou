from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.services.auth_service import AuthService
from backend.auth import hash_password
from backend.schemas.auth import ActivateInviteRequest

router = APIRouter(prefix="/api/v3/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


def _create_token_data(user_id: int, username: str, role: str) -> dict:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }


@router.post("/login")
async def login(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")

    # Bootstrap admin shortcut
    if username.lower() == settings.bootstrap_admin_username.lower():
        if password == settings.bootstrap_admin_password:
            token_data = _create_token_data(1, settings.bootstrap_admin_username, "ADMIN")
            access_token = jwt.encode(token_data, settings.secret_key, algorithm=ALGORITHM)
            response.set_cookie(
                key="access_token", value=access_token, httponly=True,
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
            return {
                "authenticated": True,
                "user": {
                    "id": 1,
                    "username": settings.bootstrap_admin_username,
                    "displayName": settings.bootstrap_admin_display_name,
                    "role": "ADMIN",
                },
            }

    # Real auth via AuthService
    auth_service = AuthService(db)
    try:
        user = await auth_service.login(username, password)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token_data = _create_token_data(user["id"], user["username"], user["role"])
    access_token = jwt.encode(token_data, settings.secret_key, algorithm=ALGORITHM)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user.get("displayName", ""),
            "role": user["role"],
        },
    }


@router.post("/activate-invite")
async def activate_invite(payload: ActivateInviteRequest, response: Response, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.activate_invite(
            payload.code,
            payload.username,
            payload.display_name,
            payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not user:
        raise HTTPException(status_code=400, detail="invite_activation_failed")

    token_data = _create_token_data(user["id"], user["username"], user["role"])
    access_token = jwt.encode(token_data, settings.secret_key, algorithm=ALGORITHM)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user.get("displayName", ""),
            "role": user["role"],
        },
    }


@router.get("/session")
async def session(request: Request):
    """Return current session from JWT token (no DB lookup needed for bootstrap admin)."""
    token = request.cookies.get("access_token")
    if not token:
        return {"authenticated": False}
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
        return {
            "authenticated": True,
            "user": {
                "id": user_id,
                "username": payload.get("username", ""),
                "displayName": "",
                "role": payload.get("role", "USER"),
            },
        }
    except JWTError:
        return {"authenticated": False}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"success": True}


async def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return {
            "id": int(payload.get("sub", "0")),
            "username": payload.get("username", ""),
            "role": payload.get("role", "USER"),
        }
    except JWTError:
        return None


async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user is None or user.get("role") != "ADMIN":
        from fastapi import HTTPException as FastHTTP
        raise FastHTTP(status_code=403, detail="Admin only")
    return user
