"""Auth endpoint tests."""
from __future__ import annotations

import pytest
from app.config import settings


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
async def test_session_unauthenticated(client):
    response = await client.get("/api/v3/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.asyncio
async def test_session_authenticated(client):
    # Login first
    login_resp = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    token = login_resp.cookies.get("access_token", "")
    # Check session with auth cookie
    response = await client.get("/api/v3/auth/session", cookies={"access_token": token})
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == settings.bootstrap_admin_username


@pytest.mark.asyncio
async def test_session_with_invalid_token(client):
    response = await client.get("/api/v3/auth/session", cookies={"access_token": "invalidtoken"})
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.asyncio
async def test_logout(client):
    # Login
    login_resp = await client.post("/api/v3/auth/login", json={
        "username": settings.bootstrap_admin_username,
        "password": settings.bootstrap_admin_password,
    })
    token = login_resp.cookies.get("access_token", "")
    # Logout
    logout_resp = await client.post("/api/v3/auth/logout", cookies={"access_token": token})
    assert logout_resp.status_code == 200
    # Verify session is cleared
    session_resp = await client.get("/api/v3/auth/session")
    assert session_resp.json()["authenticated"] is False
