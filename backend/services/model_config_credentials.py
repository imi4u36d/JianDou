"""User-scoped model credential contracts, encryption, and SQL persistence."""

from __future__ import annotations

import json
from base64 import urlsafe_b64encode
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import settings
from backend.services.model_config_values import (
    first_valid_secret,
    normalize,
    string_value,
    trim_to_empty,
)

_FERNET_PREFIX = "fernet:"


@dataclass
class RuntimeProviderConfig:
    base_url: str = ""
    task_base_url: str = ""
    extras: dict[str, str] = field(default_factory=dict)


class RuntimeModelCredentialProvider:
    """Resolve user-scoped API keys and provider endpoint overrides."""

    def find_runtime_api_key(self, user_id: int, preferred_scopes: list[str]) -> str:
        raise NotImplementedError

    def find_runtime_provider_config(self, user_id: int, preferred_scopes: list[str]) -> RuntimeProviderConfig:
        return RuntimeProviderConfig()

    def find_global_default_user_id(self) -> int | None:
        return None

    def is_admin_user(self, user_id: int) -> bool:
        return False


class MybatisUserModelCredentialRepository:
    """Persistence port retained under its compatibility name."""

    def find_api_keys_by_user_id(self, user_id: int) -> dict[str, str]:
        raise NotImplementedError

    def save_api_keys(self, user_id: int, api_keys: dict[str, str]) -> None:
        raise NotImplementedError


def protect_user_api_key(api_key: str) -> str:
    secret = first_valid_secret(api_key)
    if not secret:
        return ""
    token = _credential_fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{_FERNET_PREFIX}{token}"


def unprotect_user_api_key(stored_value: str) -> str:
    value = trim_to_empty(stored_value)
    if not value:
        return ""
    if not value.startswith(_FERNET_PREFIX):
        return first_valid_secret(value)
    token = value[len(_FERNET_PREFIX):]
    try:
        decrypted = _credential_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        return ""
    return first_valid_secret(decrypted)


def _credential_fernet() -> Fernet:
    key_material = sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(key_material))


class SqlAlchemyUserModelCredentialRepository(
    MybatisUserModelCredentialRepository,
    RuntimeModelCredentialProvider,
):
    """Persist and resolve per-user model credentials."""

    def __init__(self, database_url: str) -> None:
        self._database_url = self._sync_database_url(database_url)
        self._engine = create_engine(self._database_url, future=True)

    def find_runtime_api_key(self, user_id: int, preferred_scopes: list[str]) -> str:
        keys = self.find_api_keys_by_user_id(user_id)
        for scope in preferred_scopes:
            normalized = normalize(scope)
            for provider_key, api_key in keys.items():
                if normalize(provider_key) == normalized:
                    return first_valid_secret(api_key)
        return ""

    def find_runtime_provider_config(self, user_id: int, preferred_scopes: list[str]) -> RuntimeProviderConfig:
        rows = self.find_provider_configs_by_user_id(user_id)
        for scope in preferred_scopes:
            normalized = normalize(scope)
            for provider_key, config in rows.items():
                if normalize(provider_key) == normalized:
                    return config
        return RuntimeProviderConfig()

    def find_global_default_user_id(self) -> int | None:
        username = normalize(settings.bootstrap_admin_username)
        if not username:
            return None
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    text(
                        """
                    select id
                    from sys_user
                    where lower(username) = :username
                      and role = 'ADMIN'
                      and status = 'ACTIVE'
                    order by id asc
                    limit 1
                    """
                    ),
                    {"username": username},
                ).fetchone()
        except SQLAlchemyError:
            return None
        if row is None:
            return None
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return None

    def is_admin_user(self, user_id: int) -> bool:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    text(
                        """
                    select 1
                    from sys_user
                    where id = :user_id
                      and role = 'ADMIN'
                      and status = 'ACTIVE'
                    limit 1
                    """
                    ),
                    {"user_id": user_id},
                ).fetchone()
        except SQLAlchemyError:
            return False
        return row is not None

    def find_api_keys_by_user_id(self, user_id: int) -> dict[str, str]:
        self._ensure_table()
        keys: dict[str, str] = OrderedDict()
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    "select provider_key, encrypted_api_key "
                    "from sys_user_model_credential where user_id = :user_id"
                ),
                {"user_id": user_id},
            ).all()
        for provider_key, api_key in rows:
            key = normalize(provider_key)
            valid_api_key = unprotect_user_api_key(api_key)
            if key and valid_api_key:
                keys[key] = valid_api_key
        return keys

    def find_provider_configs_by_user_id(self, user_id: int) -> dict[str, RuntimeProviderConfig]:
        self._ensure_table()
        configs: dict[str, RuntimeProviderConfig] = OrderedDict()
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                select provider_key, base_url, task_base_url, extras_json
                from sys_user_model_credential
                where user_id = :user_id
                """
                ),
                {"user_id": user_id},
            ).all()
        for provider_key, base_url, task_base_url, extras_json in rows:
            key = normalize(provider_key)
            if not key:
                continue
            configs[key] = RuntimeProviderConfig(
                base_url=trim_to_empty(base_url),
                task_base_url=trim_to_empty(task_base_url),
                extras=self._decode_extras_json(extras_json),
            )
        return configs

    def save_api_keys(self, user_id: int, api_keys: dict[str, str]) -> None:
        normalized_updates = {
            normalize(provider): first_valid_secret(api_key)
            for provider, api_key in (api_keys or {}).items()
            if normalize(provider) and first_valid_secret(api_key)
        }
        if not normalized_updates:
            return
        self._ensure_table()
        timestamp = datetime.now(UTC).isoformat()
        with self._engine.begin() as connection:
            for provider_key, api_key in normalized_updates.items():
                protected_api_key = protect_user_api_key(api_key)
                if not protected_api_key:
                    continue
                existing = connection.execute(
                    text(
                        "select id from sys_user_model_credential "
                        "where user_id = :user_id and provider_key = :provider_key"
                    ),
                    {"user_id": user_id, "provider_key": provider_key},
                ).fetchone()
                if existing:
                    connection.execute(
                        text(
                            "update sys_user_model_credential "
                            "set encrypted_api_key = :api_key, updated_at = :updated_at where id = :id"
                        ),
                        {"api_key": protected_api_key, "updated_at": timestamp, "id": existing[0]},
                    )
                    continue
                connection.execute(
                    text(
                        """
                    insert into sys_user_model_credential
                        (user_id, provider_key, encrypted_api_key, base_url, task_base_url,
                         extras_json, created_at, updated_at)
                    values (:user_id, :provider_key, :api_key, :base_url, :task_base_url,
                            :extras_json, :created_at, :updated_at)
                    """
                    ),
                    {
                        "user_id": user_id,
                        "provider_key": provider_key,
                        "api_key": protected_api_key,
                        "base_url": "",
                        "task_base_url": "",
                        "extras_json": "{}",
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )

    def save_provider_configs(self, user_id: int, configs: dict[str, RuntimeProviderConfig]) -> None:
        normalized_updates = {
            normalize(provider): config
            for provider, config in (configs or {}).items()
            if normalize(provider)
        }
        if not normalized_updates:
            return
        self._ensure_table()
        timestamp = datetime.now(UTC).isoformat()
        with self._engine.begin() as connection:
            for provider_key, config in normalized_updates.items():
                existing = connection.execute(
                    text(
                        "select id from sys_user_model_credential "
                        "where user_id = :user_id and provider_key = :provider_key"
                    ),
                    {"user_id": user_id, "provider_key": provider_key},
                ).fetchone()
                extras_json = json.dumps(config.extras or {}, ensure_ascii=False, sort_keys=True)
                if existing:
                    connection.execute(
                        text(
                            """
                        update sys_user_model_credential
                        set base_url = :base_url, task_base_url = :task_base_url,
                            extras_json = :extras_json, updated_at = :updated_at
                        where id = :id
                        """
                        ),
                        {
                            "base_url": trim_to_empty(config.base_url),
                            "task_base_url": trim_to_empty(config.task_base_url),
                            "extras_json": extras_json,
                            "updated_at": timestamp,
                            "id": existing[0],
                        },
                    )
                    continue
                connection.execute(
                    text(
                        """
                    insert into sys_user_model_credential
                        (user_id, provider_key, encrypted_api_key, base_url, task_base_url,
                         extras_json, created_at, updated_at)
                    values (:user_id, :provider_key, :api_key, :base_url, :task_base_url,
                            :extras_json, :created_at, :updated_at)
                    """
                    ),
                    {
                        "user_id": user_id,
                        "provider_key": provider_key,
                        "api_key": "",
                        "base_url": trim_to_empty(config.base_url),
                        "task_base_url": trim_to_empty(config.task_base_url),
                        "extras_json": extras_json,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )

    def _ensure_table(self) -> None:
        return

    @staticmethod
    def _decode_extras_json(raw: str | None) -> dict[str, str]:
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, str] = {}
        for key, value in parsed.items():
            normalized_key = trim_to_empty(str(key))
            if normalized_key:
                result[normalized_key] = string_value(value)
        return result

    @staticmethod
    def _sync_database_url(database_url: str) -> str:
        if database_url.startswith("mysql+asyncmy:"):
            return database_url.replace("mysql+asyncmy:", "mysql+pymysql:", 1)
        return database_url
