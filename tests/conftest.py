"""Pytest configuration and fixtures."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.auth import hash_password
from backend.config import settings
from backend.database import Base, get_db
from backend.domain.enums import UserRole, UserStatus
from backend.models.user import SysUser


@pytest_asyncio.fixture
async def db_session_factory(tmp_path):
    """Create a fresh SQLite database and session factory for each test."""
    import backend.models  # noqa: F401

    db_path = tmp_path / "jiandou-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        now = datetime.now(UTC).isoformat()
        admin = SysUser(
            username=settings.bootstrap_admin_username,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            task_concurrency_limit=1,
            created_at=now,
            updated_at=now,
        )
        session.add(admin)
        await session.commit()

    yield async_session

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_session_factory):
    """Create one session for tests that need direct dependency overrides."""
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def clear_auth_rate_limiter():
    """Keep process-local auth rate limits isolated across tests."""
    from backend.services.auth_rate_limiter import auth_rate_limiter

    auth_rate_limiter.clear()
    yield
    auth_rate_limiter.clear()


@pytest_asyncio.fixture
async def client(db_session_factory, monkeypatch, tmp_path):
    """FastAPI test client with overridden db dependency."""
    import backend.database as database
    import backend.infrastructure.task_repository as task_repository
    from backend.main import create_app

    monkeypatch.setattr(database, "async_session_factory", db_session_factory)
    monkeypatch.setattr(task_repository, "async_session_factory", db_session_factory)
    monkeypatch.setattr(settings, "storage_root", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")

    app = create_app(start_worker=False)

    async def override_get_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        await app.state.task_repository.close()


@pytest_asyncio.fixture
async def auth_client(client):
    """Client pre-authenticated as admin."""
    response = await client.post(
        "/api/v3/auth/login",
        json={"username": settings.bootstrap_admin_username, "password": settings.bootstrap_admin_password},
    )
    assert response.status_code == 200
    token = response.cookies.get("access_token", "")
    assert token
    client.cookies.set("access_token", token)
    return client
