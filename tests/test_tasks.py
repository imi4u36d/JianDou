"""Task endpoint tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.config import settings
from backend.models.credit import SysCreditAccount, SysCreditTransaction

pytestmark = pytest.mark.api


def generation_task_payload(title: str) -> dict:
    return {
        "title": title,
        "text_analysis_model": "gpt-5.5",
        "image_model": "gpt-image-2",
        "video_model": "seedance-1.5-pro",
        "aspect_ratio": "16:9",
        "image_size": "2048x1152",
        "video_size": "1280*720",
        "video_duration_seconds": 10,
        "output_count": "auto",
    }


async def _login_as_regular_user(client, username: str = "task-credit-user") -> int:
    password = "taskcredit123"
    create_response = await client.post(
        "/api/v3/admin/users",
        json={
            "username": username,
            "password": password,
            "role": "USER",
            "status": "ACTIVE",
        },
    )
    assert create_response.status_code == 200
    user_id = create_response.json()["id"]
    client.cookies.clear()
    login_response = await client.post(
        "/api/v3/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    return user_id


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
async def test_create_video_task_consumes_user_credits(auth_client, db_session_factory):
    user_id = await _login_as_regular_user(auth_client, "task-credit-video")

    response = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Charge this video task"),
    )

    assert response.status_code == 200
    task_id = response.json().get("task_id") or response.json().get("id")
    async with db_session_factory() as session:
        account = (
            await session.execute(select(SysCreditAccount).where(SysCreditAccount.user_id == user_id))
        ).scalar_one()
        assert account.balance == 0
        assert account.total_consumed == 50

        txn = (
            await session.execute(
                select(SysCreditTransaction)
                .where(SysCreditTransaction.user_id == user_id)
                .order_by(SysCreditTransaction.id.desc())
            )
        ).scalars().first()
        assert txn is not None
        assert txn.feature_code == "VIDEO_GENERATION"
        assert txn.amount_delta == -50
        assert txn.related_task_id == task_id


@pytest.mark.asyncio
async def test_create_task_returns_402_when_user_credits_are_insufficient(auth_client):
    rule_response = await auth_client.patch(
        "/api/v3/admin/credits/rules/VIDEO_GENERATION",
        json={"cost": 60},
    )
    assert rule_response.status_code == 200
    await _login_as_regular_user(auth_client, "task-credit-low")

    response = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Too expensive task"),
    )

    assert response.status_code == 402
    assert response.json()["detail"] == "insufficient_credits"

    list_response = await auth_client.get("/api/v3/tasks")
    assert list_response.status_code == 200
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_admin_task_list_uses_owner_username(auth_client):
    await _login_as_regular_user(auth_client, "task-owner-name")
    create_response = await auth_client.post(
        "/api/v3/tasks/generation",
        json=generation_task_payload("Owner username task"),
    )
    assert create_response.status_code == 200
    task_id = create_response.json().get("task_id") or create_response.json().get("id")

    login_response = await auth_client.post(
        "/api/v3/auth/login",
        json={"username": settings.bootstrap_admin_username, "password": settings.bootstrap_admin_password},
    )
    assert login_response.status_code == 200

    response = await auth_client.get("/api/v3/admin/tasks")

    assert response.status_code == 200
    item = next(task for task in response.json()["items"] if task["id"] == task_id)
    assert item["ownerUsername"] == "task-owner-name"
    assert "ownerDisplayName" not in item


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
    assert data.get("requestSnapshot", {}).get("textAnalysisModel") == "gpt-5.5"
    assert data.get("requestSnapshot", {}).get("imageModel") == "gpt-image-2"
    assert data.get("requestSnapshot", {}).get("videoModel") == "seedance-1.5-pro"
    assert data.get("requestSnapshot", {}).get("outputCount") == {"auto": True}


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
