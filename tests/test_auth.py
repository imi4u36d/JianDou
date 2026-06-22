"""Auth endpoint tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api
import pytest
from sqlalchemy import select
from sqlalchemy import update as sa_update

from backend.config import settings
from backend.domain.enums import UserRole, UserStatus
from backend.models.user import SysUser


@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == settings.bootstrap_admin_username
    assert data["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_bootstrap_admin_is_persisted(client, db_session):
    response = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    assert response.status_code == 200

    result = await db_session.execute(
        select(SysUser).where(SysUser.username == settings.bootstrap_admin_username)
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == "ADMIN"
    assert user.status == "ACTIVE"


@pytest.mark.asyncio
async def test_login_incorrect_password(client):
    response = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    response = await client.post("/api/v3/auth/login", json={
        "username": "nonexistent",
        "password": "test123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_password_returns_422(client):
    response = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_login_rate_limit", 2)
    monkeypatch.setattr(settings, "auth_rate_limit_window_seconds", 60)

    for _ in range(2):
        response = await client.post("/api/v3/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    limited = await client.post("/api/v3/auth/login", json={
        "username": "nonexistent",
        "password": "wrongpassword",
    })

    assert limited.status_code == 429
    assert limited.json()["detail"] == "rate_limit_exceeded"
    assert "retry-after" in limited.headers


@pytest.mark.asyncio
async def test_login_rate_limit_is_scoped_by_username(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_login_rate_limit", 1)
    monkeypatch.setattr(settings, "auth_rate_limit_window_seconds", 60)

    first = await client.post("/api/v3/auth/login", json={
        "username": "first-user",
        "password": "wrongpassword",
    })
    second = await client.post("/api/v3/auth/login", json={
        "username": "second-user",
        "password": "wrongpassword",
    })

    assert first.status_code == 401
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_invite_activation_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_invite_activation_rate_limit", 1)
    monkeypatch.setattr(settings, "auth_rate_limit_window_seconds", 60)

    response = await client.post("/api/v3/auth/activate-invite", json={
        "code": "missing",
        "username": "invite-user",
        "displayName": "Invite User",
        "password": "invite123",
    })
    assert response.status_code == 400

    limited = await client.post("/api/v3/auth/activate-invite", json={
        "code": "missing",
        "username": "invite-user",
        "displayName": "Invite User",
        "password": "invite123",
    })

    assert limited.status_code == 429
    assert limited.json()["detail"] == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_session_unauthenticated(client):
    response = await client.get("/api/v3/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.asyncio
async def test_session_authenticated(client):
    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    response = await client.get("/api/v3/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == settings.bootstrap_admin_username


@pytest.mark.asyncio
async def test_session_rechecks_database_user_status(client, db_session):
    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })

    await db_session.execute(
        sa_update(SysUser)
        .where(SysUser.username == settings.bootstrap_admin_username)
        .values(status=UserStatus.DISABLED.value)
    )
    await db_session.commit()

    response = await client.get("/api/v3/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_admin_authorization_rechecks_database_role(client, db_session):
    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })

    await db_session.execute(
        sa_update(SysUser)
        .where(SysUser.username == settings.bootstrap_admin_username)
        .values(role=UserRole.USER.value)
    )
    await db_session.commit()

    response = await client.get("/api/v3/admin/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_state_changing_api_rejects_untrusted_origin(client):
    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })

    response = await client.post(
        "/api/v3/auth/logout",
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "untrusted_origin"


@pytest.mark.asyncio
async def test_state_changing_api_allows_trusted_origin(client, monkeypatch):
    monkeypatch.setattr(settings, "trusted_origins", "https://console.example")

    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })

    response = await client.post(
        "/api/v3/auth/logout",
        headers={"Origin": "https://console.example"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_session_with_invalid_token(client):
    client.cookies.set("access_token", "invalidtoken")
    response = await client.get("/api/v3/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.asyncio
async def test_logout(client):
    await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    logout_resp = await client.post("/api/v3/auth/logout")
    assert logout_resp.status_code == 200
    session_resp = await client.get("/api/v3/auth/session")
    assert session_resp.json()["authenticated"] is False
