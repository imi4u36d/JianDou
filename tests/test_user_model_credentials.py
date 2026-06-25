from __future__ import annotations

import sqlite3

import pytest

pytestmark = pytest.mark.service

from backend.services.model_config_service import (
    ModelRuntimePropertiesResolver,
    RuntimeProviderConfig,
    SqlAlchemyUserModelCredentialRepository,
)


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


def test_user_model_runtime_config_overrides_yaml_provider_values(tmp_path):
    db_path = tmp_path / "runtime-config.db"
    config_dir = tmp_path / "config"
    model_dir = config_dir / "model" / "providers"
    model_dir.mkdir(parents=True)
    (config_dir / "model" / "models.yml").write_text(
        """
model:
  models:
    "gpt-5.5":
      provider: "openai"
      vendor: "openai"
      kind: "text"
      provider_model: "gpt-5.5"
""",
        encoding="utf-8",
    )
    (model_dir / "openai.yml").write_text(
        """
model:
  providers:
    openai:
      provider: "openai"
      vendor: "openai"
      api_key: ""
      base_url: "https://wrong.example/v1"
""",
        encoding="utf-8",
    )
    repo = SqlAlchemyUserModelCredentialRepository(f"sqlite+aiosqlite:///{db_path}")
    repo.save_api_keys(7, {"openai": "sk-live-secret"})
    repo.save_provider_configs(7, {
        "openai": RuntimeProviderConfig(
            base_url="http://db.example/v1",
            extras={"timeout_seconds": "300", "use_responses_api": "false"},
        )
    })

    profile = ModelRuntimePropertiesResolver(config_dir=config_dir, credential_provider=repo).resolve_text_profile(
        "gpt-5.5", 7
    )

    assert profile.api_key == "sk-live-secret"
    assert profile.base_url == "http://db.example/v1"
    assert profile.config.timeout_seconds == 300
    assert profile.supports_responses_api() is False
