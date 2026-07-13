from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.auth_invite_service import AuthInviteService


class _ScalarResult:
    def __init__(self, value=None):  # noqa: ANN001
        self._value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self._value


@pytest.mark.asyncio
async def test_create_invite_uses_secure_code_shape_and_persists_expiry() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult()),
        add=lambda value: setattr(db, "added", value),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    service = AuthInviteService(
        db,
        lambda role: role.upper(),
        lambda code: code.strip().upper(),
        lambda username: username.strip().lower(),
        lambda password: password,
        lambda user: {"id": user.id},
    )

    result = await service.create_invite("user", 7, "2099-01-01T00:00:00+00:00")

    assert len(result["code"]) == 12
    assert result["code"].isalnum()
    assert result["role"] == "USER"
    assert result["status"] == "UNUSED"
    assert result["expiresAt"] == "2099-01-01T00:00:00+00:00"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(db.added)


@pytest.mark.parametrize(
    ("status", "message"),
    [("USED", "invite_already_used"), ("REVOKED", "invite_revoked"), ("EXPIRED", "invite_expired")],
)
def test_activate_error_message_maps_terminal_invite_status(status: str, message: str) -> None:
    assert AuthInviteService.activate_error_message(status) == message
