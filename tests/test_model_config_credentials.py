from __future__ import annotations

from backend.services.model_config_credentials import (
    SqlAlchemyUserModelCredentialRepository,
    protect_user_api_key,
    unprotect_user_api_key,
)


def test_user_api_key_round_trip_is_encrypted() -> None:
    protected = protect_user_api_key("sk-secret-value")

    assert protected.startswith("fernet:")
    assert "sk-secret-value" not in protected
    assert unprotect_user_api_key(protected) == "sk-secret-value"


def test_unprotect_accepts_legacy_plaintext_and_rejects_invalid_tokens() -> None:
    assert unprotect_user_api_key("  sk-legacy  ") == "sk-legacy"
    assert unprotect_user_api_key("fernet:not-a-token") == ""


def test_repository_helpers_normalize_driver_and_extras() -> None:
    assert (
        SqlAlchemyUserModelCredentialRepository._sync_database_url("mysql+asyncmy://user@host/db")
        == "mysql+pymysql://user@host/db"
    )
    assert SqlAlchemyUserModelCredentialRepository._decode_extras_json('{"timeout": 30, "": "skip"}') == {
        "timeout": "30"
    }
    assert SqlAlchemyUserModelCredentialRepository._decode_extras_json("not-json") == {}
