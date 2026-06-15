"""Health endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v3/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("healthy") is True
    assert "env" in data


@pytest.mark.asyncio
async def test_runtime_config(client):
    response = await client.get("/runtime-config.json")
    assert response.status_code == 200
    data = response.json()
    assert "apiBaseUrl" in data
    assert "storageBaseUrl" in data
    assert data["apiBaseUrl"] == "/api/v3"
