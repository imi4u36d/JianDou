"""Admin endpoint tests."""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.api
from backend.config import settings


async def test_admin_users_requires_auth(client):
    response = await client.get("/api/v3/admin/users")

    assert response.status_code == 401


async def test_admin_users_lists_bootstrap_admin(auth_client):
    response = await auth_client.get("/api/v3/admin/users")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    users = data["items"]
    assert any(
        user["username"] == settings.bootstrap_admin_username and user["role"] == "ADMIN"
        for user in users
    )


async def test_admin_can_create_and_update_user_with_camel_case_payload(auth_client):
    create_response = await auth_client.post(
        "/api/v3/admin/users",
        json={
            "username": "reviewer",
            "displayName": "Code Reviewer",
            "password": "reviewer123",
            "role": "USER",
            "status": "ACTIVE",
            "taskConcurrencyLimit": 3,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["username"] == "reviewer"
    assert created["displayName"] == "Code Reviewer"
    assert created["taskConcurrencyLimit"] == 3

    update_response = await auth_client.patch(
        f"/api/v3/admin/users/{created['id']}",
        json={"displayName": "Updated Reviewer", "taskConcurrencyLimit": 5},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["displayName"] == "Updated Reviewer"
    assert updated["taskConcurrencyLimit"] == 5


async def test_admin_can_create_invite_with_expires_at(auth_client):
    response = await auth_client.post(
        "/api/v3/admin/invites",
        json={"role": "USER", "expiresAt": "2099-01-01T00:00:00+00:00"},
    )

    assert response.status_code == 200
    invite = response.json()
    assert invite["role"] == "USER"
    assert invite["status"] == "UNUSED"
    assert invite["expiresAt"] == "2099-01-01T00:00:00+00:00"


async def test_admin_rejects_unknown_batch_action(auth_client):
    response = await auth_client.post(
        "/api/v3/admin/tasks/batch-action",
        json={"action": "pause", "taskIds": []},
    )

    assert response.status_code == 422


async def test_admin_rejects_negative_credit_rule_cost(auth_client):
    response = await auth_client.patch(
        "/api/v3/admin/credits/rules/IMAGE_GENERATION",
        json={"cost": -1},
    )

    assert response.status_code == 422


async def test_admin_can_adjust_user_credit_with_schema_payload(auth_client):
    create_response = await auth_client.post(
        "/api/v3/admin/users",
        json={
            "username": "credit-user",
            "displayName": "Credit User",
            "password": "credit123",
            "role": "USER",
            "status": "ACTIVE",
        },
    )
    assert create_response.status_code == 200
    user_id = create_response.json()["id"]

    response = await auth_client.post(
        f"/api/v3/admin/credits/users/{user_id}/adjust",
        json={"amount": 10, "reason": "initial test adjustment"},
    )

    assert response.status_code == 200
    credit_user = response.json()
    assert credit_user["id"] == user_id
    assert credit_user["balance"] == 60
