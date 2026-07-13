"""Per-user provider catalog assembly and credential readiness projection."""

from __future__ import annotations

import os
from collections import OrderedDict

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_contracts import AdminModelConfigResponse
from backend.services.model_config_response_support import ModelConfigResponseSupport
from backend.services.model_config_runtime import ModelRuntimePropertiesResolver
from backend.services.model_config_snapshot import string_value
from backend.services.model_config_values import (
    derive_base_url_from_host,
    first_non_blank,
    host_of,
    normalize,
    normalize_base_url,
)


class UserModelProviderCatalog(ModelConfigResponseSupport):
    """Build provider views from resolved models, config sections, and user keys."""

    def __init__(self, model_resolver: ModelRuntimePropertiesResolver) -> None:
        self._model_resolver = model_resolver

    def read_providers(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        api_keys: dict[str, str],
        user_id: int,
    ) -> list[AdminModelConfigResponse.ProviderItem]:
        vendor_models: dict[str, list[AdminModelConfigResponse.ModelItem]] = OrderedDict()
        for model in models:
            key = self._provider_group_key(model.vendor, model.provider)
            vendor_models.setdefault(key, []).append(model)

        items = [
            self._provider_item(entry_key, provider_models, api_keys, user_id)
            for entry_key, provider_models in vendor_models.items()
        ]
        existing_keys = {provider.key.lower() for provider in items}
        for section in self._model_resolver.list_sections("model.providers"):
            provider = first_non_blank(section.values.get("provider"), section.name)
            vendor = string_value(section.values.get("vendor"))
            entry_key = self._provider_group_key(vendor, provider)
            if not entry_key or normalize(entry_key) in existing_keys:
                continue
            items.append(self._config_only_provider(entry_key, provider, vendor, api_keys))
            existing_keys.add(normalize(entry_key))

        items.sort(key=lambda provider: provider.key.lower())
        return items

    def read_provider_catalog(self) -> list[AdminModelConfigResponse.ProviderItem]:
        providers: dict[str, _ProviderCatalogItem] = OrderedDict()
        for kind in (GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO):
            self._add_provider_catalog_models(providers, kind)
        for section in self._model_resolver.list_sections("model.providers"):
            provider = first_non_blank(section.values.get("provider"), section.name)
            vendor = string_value(section.values.get("vendor"))
            key = self._provider_group_key(vendor, provider)
            if key:
                providers.setdefault(key, _ProviderCatalogItem(key, provider, vendor))
        return sorted(
            (provider.to_provider_item() for provider in providers.values()),
            key=lambda provider: provider.key.lower(),
        )

    def _provider_item(
        self,
        entry_key: str,
        models: list[AdminModelConfigResponse.ModelItem],
        api_keys: dict[str, str],
        user_id: int,
    ) -> AdminModelConfigResponse.ProviderItem:
        vendor_name = first_non_blank(*[model.vendor for model in models if model.vendor], entry_key)
        base_url = self._resolve_provider_base_url(models, user_id)
        task_base_url = self._resolve_provider_task_base_url(models, user_id)
        return AdminModelConfigResponse.ProviderItem(
            key=entry_key,
            provider=vendor_name,
            vendor=vendor_name,
            kinds=list(OrderedDict.fromkeys(model.kind for model in models)),
            base_url=base_url,
            task_base_url=task_base_url,
            endpoint_host=host_of(base_url),
            task_endpoint_host=host_of(task_base_url),
            api_key_configured=any(self._is_api_key_configured(model, api_keys, user_id) for model in models),
            base_url_configured=bool(base_url),
            task_base_url_configured=bool(task_base_url),
            extras={},
            model_names=[model.name for model in models],
        )

    def _config_only_provider(
        self,
        entry_key: str,
        provider: str,
        vendor: str,
        api_keys: dict[str, str],
    ) -> AdminModelConfigResponse.ProviderItem:
        vendor_name = first_non_blank(vendor, provider, entry_key)
        base_url = self._resolve_provider_base_url_for_config(entry_key)
        return AdminModelConfigResponse.ProviderItem(
            key=entry_key,
            provider=vendor_name,
            vendor=vendor_name,
            kinds=[],
            base_url=base_url,
            task_base_url="",
            endpoint_host=host_of(base_url),
            task_endpoint_host="",
            api_key_configured=self._contains_api_key(api_keys, entry_key)
            or self._contains_api_key(api_keys, provider),
            base_url_configured=bool(base_url),
            task_base_url_configured=False,
            extras={},
            model_names=[],
        )

    def _add_provider_catalog_models(self, providers: dict[str, _ProviderCatalogItem], kind: str) -> None:
        for item in self._model_resolver.list_models_by_kind(kind):
            provider = string_value(item.get("provider"))
            vendor = string_value(item.get("vendor"))
            key = self._provider_group_key(vendor, provider) or string_value(item.get("value"))
            if not key:
                continue
            catalog_item = providers.setdefault(key, _ProviderCatalogItem(key, provider, vendor))
            catalog_item.add_kind(kind)
            catalog_item.add_model_name(string_value(item.get("value")))

    def _resolve_provider_base_url(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        user_id: int,
    ) -> str:
        for model in models:
            if model.kind == GenerationModelKinds.TEXT:
                base_url = self._model_resolver.resolve_text_profile(model.name, user_id).base_url
            else:
                base_url = self._model_resolver.resolve_media_profile(model.name, model.kind, user_id).base_url
            if base_url:
                return base_url
        return ""

    def _resolve_provider_task_base_url(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        user_id: int,
    ) -> str:
        for model in models:
            if model.kind != GenerationModelKinds.VIDEO:
                continue
            task_base_url = self._model_resolver.resolve_media_profile(
                model.name,
                model.kind,
                user_id,
            ).task_base_url
            if task_base_url:
                return task_base_url
            configured = self._model_resolver.value(
                f"model.providers.{model.provider}.extras",
                "task_base_url",
                "",
            )
            if configured:
                return configured
        return ""

    def _resolve_provider_base_url_for_config(self, provider_key: str) -> str:
        base_url = self._model_resolver.value(f"model.providers.{provider_key}", "base_url", "")
        if base_url:
            return normalize_base_url(base_url)
        env_endpoint = os.environ.get("JIANDOU_MODEL_ENDPOINT", "").strip()
        if env_endpoint:
            return normalize_base_url(env_endpoint)
        endpoint_host = os.environ.get("JIANDOU_MODEL_ENDPOINT_HOST", "").strip()
        return derive_base_url_from_host(endpoint_host) if endpoint_host else ""

    def _is_api_key_configured(
        self,
        model: AdminModelConfigResponse.ModelItem,
        api_keys: dict[str, str],
        user_id: int,
    ) -> bool:
        if self._contains_api_key(api_keys, model.vendor) or self._contains_api_key(api_keys, model.provider):
            return True
        if model.kind == GenerationModelKinds.TEXT:
            return bool(self._model_resolver.resolve_text_profile(model.name, user_id).api_key)
        return bool(self._model_resolver.resolve_media_profile(model.name, model.kind, user_id).api_key)

    @staticmethod
    def _contains_api_key(api_keys: dict[str, str], key: str) -> bool:
        normalized_key = normalize(key)
        return bool(normalized_key and api_keys and any(normalize(item) == normalized_key for item in api_keys))


class _ProviderCatalogItem:
    def __init__(self, key: str, provider: str, vendor: str) -> None:
        self.key = key
        self.provider = provider or key
        self.vendor = vendor or self.provider
        self._kinds: list[str] = []
        self._model_names: list[str] = []

    def add_kind(self, kind: str) -> None:
        if kind and kind not in self._kinds:
            self._kinds.append(kind)

    def add_model_name(self, model_name: str) -> None:
        if model_name and model_name not in self._model_names:
            self._model_names.append(model_name)

    def to_provider_item(self) -> AdminModelConfigResponse.ProviderItem:
        return AdminModelConfigResponse.ProviderItem(
            key=self.key,
            provider=self.provider,
            vendor=self.vendor,
            kinds=list(self._kinds),
            base_url="",
            task_base_url="",
            endpoint_host="",
            task_endpoint_host="",
            api_key_configured=False,
            base_url_configured=False,
            task_base_url_configured=False,
            extras={},
            model_names=list(self._model_names),
        )
