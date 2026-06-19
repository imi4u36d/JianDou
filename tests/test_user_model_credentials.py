from __future__ import annotations

import sqlite3

from backend.services.model_config_service import SqlAlchemyUserModelCredentialRepository


def test_user_model_credentials_are_encrypted_at_rest(tmp_path):
    db_path = tmp_path / "credentials.db"
    repo = SqlAlchemyUserModelCredentialRepository(f"sqlite+aiosqlite:///{db_path}")

    repo.save_api_keys(7, {"openai": "sk-live-secret"})

    with sqlite3.connect(db_path) as conn:
        stored = conn.execute(
            "select encrypted_api_key from sys_user_model_credential where user_id = ? and provider_key = ?",
            (7, "openai"),
        ).fetchone()[0]

    assert stored.startswith("fernet:")
    assert stored != "sk-live-secret"
    assert "sk-live-secret" not in stored
    assert repo.find_runtime_api_key(7, ["openai"]) == "sk-live-secret"


def test_user_model_credentials_still_read_legacy_plaintext(tmp_path):
    db_path = tmp_path / "legacy-credentials.db"
    repo = SqlAlchemyUserModelCredentialRepository(f"sqlite+aiosqlite:///{db_path}")
    repo.save_api_keys(1, {"seed": "sk-seed"})

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            insert into sys_user_model_credential
                (user_id, provider_key, encrypted_api_key, created_at, updated_at)
            values (?, ?, ?, ?, ?)
            """,
            (9, "openai", "sk-legacy-secret", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    assert repo.find_runtime_api_key(9, ["openai"]) == "sk-legacy-secret"
