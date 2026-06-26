"""User-facing credit endpoint tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api

from backend.auth import create_access_token, create_token_data, hash_password
from backend.domain.enums import UserRole, UserStatus
from backend.models.credit import SysCreditTransaction
from backend.models.user import SysUser


async def _create_user_session(client, db_session_factory, *, username: str) -> int:
    async with db_session_factory() as session:
        user = SysUser(
            username=username,
            password_hash=hash_password("test-password"),
            role=UserRole.USER.value,
            status=UserStatus.ACTIVE.value,
            task_concurrency_limit=1,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = int(user.id)
    token = create_access_token(create_token_data(user_id, username, UserRole.USER.value))
    client.cookies.set("access_token", token)
    return user_id


def _transaction(user_id: int, index: int, *, created_at: str) -> SysCreditTransaction:
    return SysCreditTransaction(
        transaction_id=f"credit_test_{user_id}_{index}",
        user_id=user_id,
        feature_code="IMAGE_GENERATION",
        transaction_type="CONSUME",
        amount_delta=-5,
        balance_before=50 - index * 5,
        balance_after=45 - index * 5,
        related_run_id="",
        related_task_id=f"task_{index}",
        related_workflow_id="",
        reason="test consume",
        metadata_json="{}",
        created_at=created_at,
    )


async def test_credit_transactions_require_auth(client):
    response = await client.get("/api/v3/credits/transactions")

    assert response.status_code == 401


async def test_current_user_credit_transactions_are_paginated(client, db_session_factory):
    user_id = await _create_user_session(client, db_session_factory, username="credit-reader")
    other_user_id = user_id + 1000
    async with db_session_factory() as session:
        session.add_all(
            [
                _transaction(user_id, 1, created_at="2026-01-01T00:00:00+00:00"),
                _transaction(user_id, 2, created_at="2026-01-02T00:00:00+00:00"),
                _transaction(user_id, 3, created_at="2026-01-03T00:00:00+00:00"),
                _transaction(other_user_id, 1, created_at="2026-01-04T00:00:00+00:00"),
            ]
        )
        await session.commit()

    response = await client.get("/api/v3/credits/transactions?offset=0&limit=2")

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert page["offset"] == 0
    assert page["limit"] == 2
    assert [item["transactionId"] for item in page["items"]] == [
        f"credit_test_{user_id}_3",
        f"credit_test_{user_id}_2",
    ]
