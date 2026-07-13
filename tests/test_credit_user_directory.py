from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.credit_user_directory import CreditUserDirectory


class _ScalarResult:
    def __init__(self, values):  # noqa: ANN001
        self._values = values

    def scalars(self):  # noqa: ANN201
        return self

    def all(self):  # noqa: ANN201
        return list(self._values)


@pytest.mark.asyncio
async def test_credit_user_directory_aggregates_accounts_and_usage() -> None:
    user = SimpleNamespace(id=7, username="reader", role="USER", status="ACTIVE")
    account = SimpleNamespace(user_id=7, balance=80, total_consumed=60, total_adjusted=40)
    transactions = [
        SimpleNamespace(user_id=7, feature_code="IMAGE_GENERATION", created_at="2026-07-10T00:00:00Z"),
        SimpleNamespace(user_id=7, feature_code="VIDEO_GENERATION", created_at="2026-07-11T00:00:00Z"),
    ]
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_ScalarResult([user]), _ScalarResult([account]), _ScalarResult(transactions)]),
        commit=AsyncMock(),
    )
    ensure_account = AsyncMock()
    directory = CreditUserDirectory(db, ensure_account, 50)

    result = await directory.list_users("read")

    ensure_account.assert_awaited_once_with(7, 50)
    db.commit.assert_awaited_once()
    assert result == [{
        "id": 7,
        "username": "reader",
        "role": "USER",
        "status": "ACTIVE",
        "balance": 80,
        "totalConsumed": 60,
        "totalAdjusted": 40,
        "imageGenerationCount": 1,
        "videoGenerationCount": 1,
        "lastUsedAt": "2026-07-11T00:00:00Z",
    }]
