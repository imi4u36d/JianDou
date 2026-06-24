"""Task endpoint tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api


def generation_task_payload(title: str) -> dict:
    return {
        "title": title,
        "text_analysis_model": "deepseek-v4-flash",
        "image_model": "Doubao-Seedream-5.0-Lite",
        "video_model": "seedance-1.5-pro",
        "aspect_ratio": "16:9",
        "image_size": "2560x1440",
        "video_size": "1280*720",
        "video_duration_seconds": 10,
    }


@pytest.mark.asyncio
async def test_list_tasks_empty(auth_client):
    response = await auth_client.get("/api/v3/tasks")
    assert response.status_code == 200
    data = response.json()
    # The endpoint returns a dict or list depending on implementation
    # Accept both shapes gracefully
    if isinstance(data, list):
        assert len(data) == 0
    elif isinstance(data, dict):
        assert "items" in data


@pytest.mark.asyncio
async def test_create_task(auth_client):
    """POST /api/v3/tasks/generation creates a task."""
    response = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Test Task from pytest"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Test Task from pytest"
    assert data.get("task_id") or data.get("id")


@pytest.mark.asyncio
async def test_create_and_get_task(auth_client):
    # Create a task
    create_resp = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Get this task"),
    )
    task_id = create_resp.json().get("task_id") or create_resp.json().get("id")
    # Get by ID
    response = await auth_client.get(f"/api/v3/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Get this task"


@pytest.mark.asyncio
async def test_get_nonexistent_task_returns_404(auth_client):
    response = await auth_client.get("/api/v3/tasks/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(auth_client):
    # Create first
    create_resp = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Delete me"),
    )
    task_id = create_resp.json().get("task_id") or create_resp.json().get("id")
    # Delete
    del_resp = await auth_client.delete(f"/api/v3/tasks/{task_id}")
    assert del_resp.status_code == 200
    # Verify it's gone
    get_resp = await auth_client.get(f"/api/v3/tasks/{task_id}")
    assert get_resp.status_code == 404
