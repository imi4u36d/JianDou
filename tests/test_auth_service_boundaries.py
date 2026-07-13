from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.services.auth_service import AuthService, validate_password
from backend.services.auth_user_service import AuthUserService
from backend.services.auth_values import (
    normalize_invite_code,
    normalize_user_role,
    normalize_username,
)

pytestmark = pytest.mark.service


def test_auth_facade_composes_user_and_invite_lifecycles() -> None:
    service = AuthService(object())

    assert isinstance(service._user_service, AuthUserService)
    assert service._invite_service is not None


@pytest.mark.asyncio
async def test_auth_facade_delegates_session_login() -> None:
    service = AuthService(object())
    service._user_service.login = AsyncMock(return_value={"id": 7, "username": "alice"})

    result = await service.login("Alice", "password123")

    assert result == {"id": 7, "username": "alice"}
    service._user_service.login.assert_awaited_once_with("Alice", "password123")


def test_auth_values_remain_available_through_stable_facade() -> None:
    assert normalize_username(" Alice ") == "alice"
    assert normalize_invite_code(" ab-cd ") == "AB-CD"
    assert normalize_user_role("admin") == "ADMIN"
    assert validate_password("password123") == "password123"
