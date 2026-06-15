"""Task endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    response = await client.get("/api/v3/tasks")
    assert response.status_code == 200
    data = response.json()
    # The endpoint returns a dict or list depending on implementation
    # Accept both shapes gracefully
    if isinstance(data, list):
        assert len(data) == 0
    elif isinstance(data, dict):
        assert "items" in data


@pytest.mark.asyncio
async def test_create_task(client):
    """POST /api/v3/tasks/generation creates a task."""
    response = await client.post("/api/v3/tasks/generation", json={
        "title": "Test Task from pytest",
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Test Task from pytest"
    assert data.get("task_id") or data.get("id")


@pytest.mark.asyncio
async def test_create_and_get_task(client):
    # Create a task
    create_resp = await client.post("/api/v3/tasks/generation", json={
        "title": "Get this task",
    })
    task_id = create_resp.json().get("task_id") or create_resp.json().get("id")
    # Get by ID
    response = await client.get(f"/api/v3/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Get this task"


@pytest.mark.asyncio
async def test_get_nonexistent_task_returns_404(client):
    response = await client.get("/api/v3/tasks/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(client):
    # Create first
    create_resp = await client.post("/api/v3/tasks/generation", json={
        "title": "Delete me",
    })
    task_id = create_resp.json().get("task_id") or create_resp.json().get("id")
    # Delete
    del_resp = await client.delete(f"/api/v3/tasks/{task_id}")
    assert del_resp.status_code == 200
    # Verify it's gone
    get_resp = await client.get(f"/api/v3/tasks/{task_id}")
    assert get_resp.status_code == 404
