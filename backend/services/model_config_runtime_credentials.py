"""User and environment credential resolution for runtime model profiles."""

from __future__ import annotations

import os
import re

from backend.services.model_config_credentials import RuntimeModelCredentialProvider, RuntimeProviderConfig
from backend.services.model_config_snapshot import ConfigSnapshot
from backend.services.model_config_values import (
    first_non_blank,
    first_valid_secret,
    normalize,
    trim_to_empty,
)


def env_value(key: str) -> str:
    return os.environ.get(key, "").strip()


def scoped_property(scope: str | None, suffix: str) -> str:
    namespace = trim_to_empty(scope)
    if not namespace:
        return ""
    normalized = re.sub(r"[^A-Z0-9]+", "_", namespace.upper())
    return env_value(f"JIANDOU_MODEL_{normalized}_{suffix}")


def provider_property(provider: str, suffix: str) -> str:
    return scoped_property(provider, suffix)


def vendor_property(vendor: str, suffix: str) -> str:
    return scoped_property(vendor, suffix)


def resolve_config_source(
    user_scoped: bool,
    api_key: str,
    provider: str,
    vendor: str,
    default_source: str,
    provider_overridden: bool,
) -> str:
    if user_scoped:
        return default_source if not api_key else "user-db"
    if (
        env_value("JIANDOU_MODEL_API_KEY")
        or provider_property(provider, "API_KEY")
        or vendor_property(vendor, "API_KEY")
        or env_value("JIANDOU_MODEL_BASE_URL")
        or provider_property(provider, "BASE_URL")
        or provider_property(provider, "TASK_BASE_URL")
        or provider_overridden
    ):
        return "env"
    return default_source


class RuntimeCredentialResolver:
    """Apply user scope, global-admin fallback, and sibling-provider credential rules."""

    def __init__(self, credential_provider: RuntimeModelCredentialProvider | None) -> None:
        self._credential_provider = credential_provider

    def resolve_api_key(
        self,
        current: ConfigSnapshot,
        user_id: int | None,
        provider: str,
        vendor: str,
        provider_section: str,
    ) -> str:
        if user_id is not None:
            return self._resolve_user_api_key(current, user_id, provider, vendor)
        return first_valid_secret(
            env_value("JIANDOU_MODEL_API_KEY"),
            provider_property(provider, "API_KEY"),
            vendor_property(vendor, "API_KEY"),
            current.value(f"model.providers.{vendor}", "api_key") if vendor else "",
            current.value(provider_section, "api_key"),
            self._resolve_shared_configured_api_key(current, provider, vendor),
            "",
        )

    def resolve_user_provider_config(
        self, current: ConfigSnapshot, user_id: int | None, provider: str, vendor: str
    ) -> RuntimeProviderConfig:
        if user_id is None or self._credential_provider is None:
            return RuntimeProviderConfig()
        preferred_scopes = self._preferred_api_key_scopes(current, provider, vendor)
        merged = RuntimeProviderConfig()
        for credential_user_id in reversed(self._runtime_credential_user_ids(user_id)):
            config = self._credential_provider.find_runtime_provider_config(credential_user_id, preferred_scopes)
            if config.base_url:
                merged.base_url = config.base_url
            if config.task_base_url:
                merged.task_base_url = config.task_base_url
            if config.extras:
                merged.extras.update({key: value for key, value in config.extras.items() if trim_to_empty(value)})
        return merged

    def _resolve_user_api_key(self, current: ConfigSnapshot, user_id: int, provider: str, vendor: str) -> str:
        if self._credential_provider is None:
            return ""
        preferred_scopes = self._preferred_api_key_scopes(current, provider, vendor)
        for credential_user_id in self._runtime_credential_user_ids(user_id):
            api_key = first_valid_secret(
                self._credential_provider.find_runtime_api_key(credential_user_id, preferred_scopes)
            )
            if api_key:
                return api_key
        return ""

    def _runtime_credential_user_ids(self, user_id: int) -> list[int]:
        if self._credential_provider is None:
            return [user_id]
        if self._credential_provider.is_admin_user(user_id):
            return [user_id]
        default_user_id = self._credential_provider.find_global_default_user_id()
        return [default_user_id] if default_user_id is not None else []

    def _preferred_api_key_scopes(self, current: ConfigSnapshot, provider: str, vendor: str) -> list[str]:
        scopes: list[str] = []
        self._add_api_key_scope(scopes, provider)
        for sibling in self._same_vendor_provider_keys(current, provider, vendor):
            self._add_api_key_scope(scopes, sibling)
        self._add_api_key_scope(scopes, vendor)
        return scopes

    def _resolve_shared_configured_api_key(self, current: ConfigSnapshot, provider: str, vendor: str) -> str:
        for sibling in self._same_vendor_provider_keys(current, provider, vendor):
            api_key = current.value(f"model.providers.{sibling}", "api_key")
            if first_valid_secret(api_key):
                return api_key
        return ""

    def _same_vendor_provider_keys(self, current: ConfigSnapshot, provider: str, vendor: str) -> list[str]:
        normalized_vendor = normalize(vendor)
        if not normalized_vendor:
            return []
        keys: list[str] = []
        for section in current.list_sections("model.providers"):
            if normalized_vendor != normalize(first_non_blank(section.values.get("vendor"))):
                continue
            self._add_api_key_scope(keys, section.name)
            self._add_api_key_scope(keys, section.values.get("provider"))
        return [key for key in keys if normalize(key) != normalize(provider)]

    @staticmethod
    def _add_api_key_scope(scopes: list[str], candidate: str) -> None:
        normalized_candidate = trim_to_empty(candidate)
        if normalized_candidate and not any(normalize(scope) == normalize(normalized_candidate) for scope in scopes):
            scopes.append(normalized_candidate)
