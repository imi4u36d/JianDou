from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    create_access_token,
    create_token_data,
    delete_auth_cookie,
    get_current_user,
    set_auth_cookie,
)
from backend.config import settings
from backend.database import get_db
from backend.schemas.auth import ActivateInviteRequest, LoginRequest
from backend.services.auth_rate_limiter import check_auth_subject_rate_limit
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/v3/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    check_auth_subject_rate_limit(request, "auth.login", payload.username, settings.auth_login_rate_limit)
    auth_service = AuthService(db)
    try:
        user = await auth_service.login(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not user and payload.username.lower() == settings.bootstrap_admin_username.lower():
        if payload.password == settings.bootstrap_admin_password:
            user = await auth_service.ensure_bootstrap_admin(
                settings.bootstrap_admin_username,
                settings.bootstrap_admin_display_name,
                settings.bootstrap_admin_password,
            )

    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token_data = create_token_data(user["id"], user["username"], user["role"])
    access_token = create_access_token(token_data)
    set_auth_cookie(response, access_token)
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
async def activate_invite(
    payload: ActivateInviteRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    check_auth_subject_rate_limit(
        request,
        "auth.activate_invite",
        payload.code,
        settings.auth_invite_activation_rate_limit,
    )
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

    token_data = create_token_data(user["id"], user["username"], user["role"])
    access_token = create_access_token(token_data)
    set_auth_cookie(response, access_token)
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
    """Return the current active database-backed session."""
    user = await get_current_user(request)
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user.get("displayName", ""),
            "role": user["role"],
        },
    }


@router.post("/logout")
async def logout(response: Response):
    delete_auth_cookie(response)
    return {"success": True}
