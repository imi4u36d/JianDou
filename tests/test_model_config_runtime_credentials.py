from __future__ import annotations

import pytest

from backend.services.model_config_credentials import RuntimeModelCredentialProvider, RuntimeProviderConfig
from backend.services.model_config_runtime_credentials import RuntimeCredentialResolver, resolve_config_source
from backend.services.model_config_snapshot import ConfigSnapshot

pytestmark = pytest.mark.service


class _CredentialProvider(RuntimeModelCredentialProvider):
    def __init__(self) -> None:
        self.requested_api_keys: list[tuple[int, list[str]]] = []
        self.requested_configs: list[tuple[int, list[str]]] = []

    def find_runtime_api_key(self, user_id: int, preferred_scopes: list[str]) -> str:
        self.requested_api_keys.append((user_id, preferred_scopes))
        return {7: "admin-key", 9: "user-key"}.get(user_id, "")

    def find_runtime_provider_config(self, user_id: int, preferred_scopes: list[str]) -> RuntimeProviderConfig:
        self.requested_configs.append((user_id, preferred_scopes))
        return RuntimeProviderConfig(base_url=f"https://user-{user_id}.example/v1", extras={"timeout_seconds": "300"})

    def find_global_default_user_id(self) -> int | None:
        return 7

    def is_admin_user(self, user_id: int) -> bool:
        return user_id == 7


def _snapshot() -> ConfigSnapshot:
    return ConfigSnapshot(
        {
            "model": {
                "providers": {
                    "openai-chat": {"provider": "openai-chat", "vendor": "openai"},
                    "openai-image": {"provider": "openai-image", "vendor": "openai"},
                    "other": {"provider": "other", "vendor": "other"},
                }
            }
        },
        "test",
        [],
    )


def test_regular_users_resolve_through_global_default_with_sibling_scopes() -> None:
    provider = _CredentialProvider()
    resolver = RuntimeCredentialResolver(provider)

    api_key = resolver.resolve_api_key(_snapshot(), 9, "openai-chat", "openai", "model.providers.openai-chat")
    config = resolver.resolve_user_provider_config(_snapshot(), 9, "openai-chat", "openai")

    assert api_key == "admin-key"
    assert config.base_url == "https://user-7.example/v1"
    assert provider.requested_api_keys == [(7, ["openai-chat", "openai-image", "openai"])]
    assert provider.requested_configs == [(7, ["openai-chat", "openai-image", "openai"])]


def test_admin_users_keep_their_own_runtime_credentials() -> None:
    provider = _CredentialProvider()
    resolver = RuntimeCredentialResolver(provider)

    assert resolver.resolve_api_key(_snapshot(), 7, "openai-chat", "openai", "model.providers.openai-chat") == "admin-key"
    assert provider.requested_api_keys[0][0] == 7


def test_config_source_reports_environment_and_user_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JIANDOU_MODEL_API_KEY", raising=False)
    assert resolve_config_source(True, "user-key", "openai", "openai", "file:test", False) == "user-db"
    assert resolve_config_source(False, "", "openai", "openai", "file:test", False) == "file:test"

    monkeypatch.setenv("JIANDOU_MODEL_OPENAI_BASE_URL", "https://env.example/v1")
    assert resolve_config_source(False, "", "openai", "openai", "file:test", False) == "env"
