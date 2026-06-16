"""Pytest configuration and fixtures."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.config import settings


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client with overridden db dependency."""
    from backend.main import create_app

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client, db_session):
    """Client pre-authenticated as admin."""
    # Login as admin
    response = await client.post(
        "/api/v3/auth/login",
        json={"username": settings.bootstrap_admin_username, "password": settings.bootstrap_admin_password},
    )
    assert response.status_code == 200
    token = response.cookies.get("access_token", "")
    return client, {"access_token": token}
