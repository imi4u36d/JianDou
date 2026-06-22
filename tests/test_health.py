"""Health endpoint tests."""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.api
import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v3/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("healthy") is True
    assert "env" in data
    assert "database_url" not in str(data)
    assert data["runtime"]["database"]["configured"] is True
    assert "dialect" in data["runtime"]["database"]


@pytest.mark.asyncio
async def test_ready(client):
    response = await client.get("/api/v3/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["checks"]["database"]["ready"] is True
    assert data["checks"]["storage"]["ready"] is True
    assert "database_url" not in str(data)


@pytest.mark.asyncio
async def test_ready_reports_database_failure(client, monkeypatch):
    import backend.database as database

    class FailingSessionFactory:
        def __call__(self):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(database, "async_session_factory", FailingSessionFactory())

    response = await client.get("/api/v3/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["ready"] is False
    assert data["checks"]["database"]["ready"] is False
    assert data["checks"]["database"]["detail"] == "RuntimeError"


@pytest.mark.asyncio
async def test_security_headers_are_sent(client):
    response = await client.get("/api/v3/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "strict-transport-security" not in response.headers


@pytest.mark.asyncio
async def test_hsts_is_sent_when_secure_cookies_are_enabled(client, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "cookie_secure", True)

    response = await client.get("/api/v3/health")
    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.asyncio
async def test_runtime_config(client):
    response = await client.get("/runtime-config.json")
    assert response.status_code == 200
    data = response.json()
    assert "apiBaseUrl" in data
    assert "storageBaseUrl" in data
    assert data["apiBaseUrl"] == "/api/v3"
