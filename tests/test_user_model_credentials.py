from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field

import pytest
from sqlalchemy import create_engine, text

from backend.config import settings
from backend.services.model_config_service import (
    ModelRuntimePropertiesResolver,
    RuntimeProviderConfig,
    SqlAlchemyUserModelCredentialRepository,
)

pytestmark = pytest.mark.service


@dataclass
class CredentialStore:
    database_url: str
    engine: object
    admin_username: str
    suffix: str
    user_ids: list[int] = field(default_factory=list)

    def next_user_id(self) -> int:
        user_id = 100_000 + (uuid.uuid4().int % 900_000_000)
        self.user_ids.append(user_id)
        return user_id


@pytest.fixture
def credential_store(monkeypatch):
    database_url = os.environ.get("JIANDOU_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set JIANDOU_TEST_DATABASE_URL to run credential repository integration tests.")
    if "test" not in database_url.lower():
        pytest.skip("JIANDOU_TEST_DATABASE_URL must point at a disposable test database.")

    sync_url = SqlAlchemyUserModelCredentialRepository._sync_database_url(database_url)
    engine = create_engine(sync_url, future=True)
    suffix = uuid.uuid4().hex[:12]
    admin_username = f"admin-{suffix}"
    monkeypatch.setattr(settings, "bootstrap_admin_username", admin_username)

    _ensure_tables(engine)
    store = CredentialStore(database_url=database_url, engine=engine, admin_username=admin_username, suffix=suffix)

    yield store

    if store.user_ids:
        with engine.begin() as conn:
            for user_id in store.user_ids:
                conn.execute(text("delete from sys_user_model_credential where user_id = :user_id"), {"user_id": user_id})
                conn.execute(text("delete from sys_user where id = :user_id"), {"user_id": user_id})
    engine.dispose()


def _ensure_tables(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                create table if not exists sys_user (
                    id integer not null auto_increment,
                    username varchar(64) not null,
                    password_hash varchar(255) not null,
                    role varchar(16) not null,
                    status varchar(16) not null,
                    last_login_at varchar(32),
                    task_concurrency_limit integer not null,
                    created_at varchar(32) not null,
                    updated_at varchar(32) not null,
                    primary key (id),
                    unique key ux_sys_user_username (username)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                create table if not exists sys_user_model_credential (
                    id integer not null auto_increment,
                    user_id integer not null,
                    provider_key varchar(64) not null,
                    encrypted_api_key varchar(255) not null,
                    base_url varchar(1024) not null,
                    task_base_url varchar(1024) not null,
                    extras_json varchar(2048) not null,
                    created_at varchar(32) not null,
                    updated_at varchar(32) not null,
                    primary key (id),
                    unique key ux_sys_user_model_credential_user_provider (user_id, provider_key)
                )
                """
            )
        )


def _create_user(store: CredentialStore, user_id: int, username: str, role: str) -> None:
    with store.engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into sys_user
                    (id, username, password_hash, role, status,
                     task_concurrency_limit, created_at, updated_at)
                values (:id, :username, :password_hash, :role, :status,
                        :task_concurrency_limit, :created_at, :updated_at)
                on duplicate key update
                    username = values(username),
                    password_hash = values(password_hash),
                    role = values(role),
                    status = values(status),
                    task_concurrency_limit = values(task_concurrency_limit),
                    updated_at = values(updated_at)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": "hash",
                "role": role,
                "status": "ACTIVE",
                "task_concurrency_limit": 1,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        )


def _create_admin(store: CredentialStore, admin_id: int) -> None:
    _create_user(store, admin_id, store.admin_username, "ADMIN")


def _create_regular_user(store: CredentialStore, user_id: int) -> None:
    _create_user(store, user_id, f"user-{store.suffix}-{user_id}", "USER")


def _stored_credential(store: CredentialStore, user_id: int, provider_key: str) -> tuple:
    with store.engine.connect() as conn:
        return conn.execute(
            text(
                """
                select encrypted_api_key, base_url, task_base_url, extras_json
                from sys_user_model_credential
                where user_id = :user_id and provider_key = :provider_key
                """
            ),
            {"user_id": user_id, "provider_key": provider_key},
        ).fetchone()


def test_user_model_credentials_are_encrypted_at_rest(credential_store):
    user_id = credential_store.next_user_id()
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)

    repo.save_api_keys(user_id, {"openai": "sk-live-secret"})

    stored = _stored_credential(credential_store, user_id, "openai")[0]

    assert stored.startswith("fernet:")
    assert stored != "sk-live-secret"
    assert "sk-live-secret" not in stored
    assert repo.find_runtime_api_key(user_id, ["openai"]) == "sk-live-secret"


def test_user_model_credentials_still_read_legacy_plaintext(credential_store):
    seed_user_id = credential_store.next_user_id()
    legacy_user_id = credential_store.next_user_id()
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)
    repo.save_api_keys(seed_user_id, {"seed": "sk-seed"})

    with credential_store.engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into sys_user_model_credential
                    (user_id, provider_key, encrypted_api_key, base_url, task_base_url,
                     extras_json, created_at, updated_at)
                values (:user_id, :provider_key, :api_key, '', '', '{}',
                        :created_at, :updated_at)
                """
            ),
            {
                "user_id": legacy_user_id,
                "provider_key": "openai",
                "api_key": "sk-legacy-secret",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        )

    assert repo.find_runtime_api_key(legacy_user_id, ["openai"]) == "sk-legacy-secret"


def test_user_model_credentials_insert_runtime_columns_without_server_defaults(credential_store):
    user_id = credential_store.next_user_id()
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)

    repo.save_api_keys(user_id, {"openai": "sk-live-secret"})

    stored = _stored_credential(credential_store, user_id, "openai")

    assert stored[1:] == ("", "", "{}")
    assert repo.find_runtime_api_key(user_id, ["openai"]) == "sk-live-secret"


def test_user_model_runtime_config_overrides_yaml_provider_values(credential_store, tmp_path):
    admin_id = credential_store.next_user_id()
    _create_admin(credential_store, admin_id)
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
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)
    repo.save_api_keys(admin_id, {"openai": "sk-live-secret"})
    repo.save_provider_configs(admin_id, {
        "openai": RuntimeProviderConfig(
            base_url="http://db.example/v1",
            extras={"timeout_seconds": "300", "use_responses_api": "false"},
        )
    })

    profile = ModelRuntimePropertiesResolver(config_dir=config_dir, credential_provider=repo).resolve_text_profile(
        "gpt-5.5", admin_id
    )

    assert profile.api_key == "sk-live-secret"
    assert profile.base_url == "http://db.example/v1"
    assert profile.config.timeout_seconds == 300
    assert profile.supports_responses_api() is False


def test_user_model_runtime_config_falls_back_to_admin_default_key(credential_store, tmp_path):
    admin_id = credential_store.next_user_id()
    target_user_id = credential_store.next_user_id()
    _create_admin(credential_store, admin_id)
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
      base_url: "https://yaml.example/v1"
""",
        encoding="utf-8",
    )
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)
    repo.save_api_keys(admin_id, {"openai": "sk-admin-default"})
    repo.save_provider_configs(admin_id, {
        "openai": RuntimeProviderConfig(
            base_url="https://admin.example/v1",
            extras={"timeout_seconds": "300"},
        )
    })

    profile = ModelRuntimePropertiesResolver(config_dir=config_dir, credential_provider=repo).resolve_text_profile(
        "gpt-5.5", target_user_id
    )

    assert profile.api_key == "sk-admin-default"
    assert profile.base_url == "https://admin.example/v1"
    assert profile.config.timeout_seconds == 300


def test_user_model_runtime_config_ignores_regular_user_key_before_admin_default(credential_store, tmp_path):
    admin_id = credential_store.next_user_id()
    regular_user_id = credential_store.next_user_id()
    _create_admin(credential_store, admin_id)
    _create_regular_user(credential_store, regular_user_id)
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
      base_url: "https://yaml.example/v1"
""",
        encoding="utf-8",
    )
    repo = SqlAlchemyUserModelCredentialRepository(credential_store.database_url)
    repo.save_api_keys(admin_id, {"openai": "sk-admin-default"})
    repo.save_api_keys(regular_user_id, {"openai": "sk-user-override"})

    profile = ModelRuntimePropertiesResolver(config_dir=config_dir, credential_provider=repo).resolve_text_profile(
        "gpt-5.5", regular_user_id
    )

    assert profile.api_key == "sk-admin-default"
