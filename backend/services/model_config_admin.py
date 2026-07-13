"""Administrative model catalog responses and platform secret persistence."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_contracts import (
    AdminModelConfigKeyUpdateRequest,
    AdminModelConfigResponse,
    AdminModelConfigValidationResponse,
)
from backend.services.model_config_response_support import ModelConfigResponseSupport
from backend.services.model_config_runtime import ModelRuntimePropertiesResolver
from backend.services.model_config_snapshot import string_value as _string_value
from backend.services.model_config_values import bool_value as _bool_value
from backend.services.model_config_values import double_value as _double_value
from backend.services.model_config_values import first_non_blank as _first_non_blank
from backend.services.model_config_values import host_of as _host_of
from backend.services.model_config_values import normalize as _normalize
from backend.services.model_config_values import parse_integer_list as _parse_integer_list
from backend.services.model_config_values import parse_string_list as _parse_string_list


class AdminModelConfigService(ModelConfigResponseSupport):
    """Admin operations for model configuration.

    Mirrors the Java AdminModelConfigService.
    """

    KIND_ORDER = [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO]
    MISSING_API_KEY_ISSUE = "缺少 api_key"

    def __init__(
        self,
        model_resolver: ModelRuntimePropertiesResolver,
        secrets_service: AdminModelConfigSecretsService | None = None,
    ):
        self._model_resolver = model_resolver
        self._secrets_service = secrets_service

    def read(self) -> AdminModelConfigResponse:
        models: list[AdminModelConfigResponse.ModelItem] = []
        models.extend(self._read_text_models(GenerationModelKinds.TEXT))
        models.extend(self._read_media_models(GenerationModelKinds.IMAGE))
        models.extend(self._read_media_models(GenerationModelKinds.VIDEO))
        models.sort(key=lambda m: (self._kind_index(m.kind), m.name.lower()))

        providers = self._read_providers(models)
        return AdminModelConfigResponse(
            config_source=self._model_resolver.config_source(),
            summary=self._build_summary(models, providers),
            defaults=self._read_defaults(),
            providers=providers,
            models=list(models),
            config_errors=list(self._model_resolver.config_errors()),
        )

    def validate_keys(self, request: AdminModelConfigKeyUpdateRequest) -> AdminModelConfigValidationResponse:
        current = self.read()
        snapshot = self._apply_api_key_overrides(current, self._collect_api_key_updates(request, current.providers))
        valid = not snapshot.config_errors and all(m.ready for m in snapshot.models)
        return AdminModelConfigValidationResponse(valid=valid, snapshot=snapshot)

    def save_keys(self, request: AdminModelConfigKeyUpdateRequest) -> AdminModelConfigResponse:
        current = self.read()
        updates = self._collect_api_key_updates(request, current.providers)
        if updates.errors:
            raise ValueError(" / ".join(updates.errors))
        if updates.api_keys:
            if self._secrets_service:
                self._secrets_service.save_api_keys(updates.api_keys)
            self._model_resolver.refresh()
        return self.read()

    # ---- Private helpers --------------------------------------------------

    def _read_defaults(self) -> AdminModelConfigResponse.Defaults:
        return AdminModelConfigResponse.Defaults(
            default_aspect_ratio=self._model_resolver.value("pipeline", "default_aspect_ratio", "9:16"),
            image_size=self._model_resolver.value("catalog.defaults", "image_size", "1024x1024"),
            video_size=self._model_resolver.value("catalog.defaults", "video_size", "720*1280"),
            video_duration_seconds=self._model_resolver.int_value("catalog.defaults", "video_duration_seconds", 8),
            timeout_seconds=self._model_resolver.int_value("model", "timeout_seconds", 120),
            temperature=_double_value(self._model_resolver.value("model", "temperature", "0.15"), 0.15),
            max_tokens=self._model_resolver.int_value("model", "max_tokens", 2000),
        )

    def _read_text_models(self, kind: str) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_text_profile(name)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            items.append(
                AdminModelConfigResponse.ModelItem(
                    name=name,
                    label=_first_non_blank(_string_value(item.get("label")), name),
                    kind=kind,
                    provider=profile.provider,
                    vendor=_string_value(item.get("vendor")),
                    family=_string_value(item.get("family")),
                    description=_string_value(item.get("description")),
                    supports_seed=_bool_value(str(item.get("supportsSeed", ""))),
                    supports_responses_api=_bool_value(str(item.get("supportsResponsesApi", ""))),
                    generation_mode="",
                    supported_sizes=[],
                    supported_durations=[],
                    ready=not issues and profile.ready,
                    config_source=profile.source,
                    endpoint_host=profile.endpoint_host,
                    task_endpoint_host="",
                    issues=issues,
                )
            )
        return items

    def _read_media_models(self, kind: str) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_media_profile(name, kind)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            if kind == GenerationModelKinds.VIDEO and not profile.task_base_url:
                issues.append("缺少 task_base_url")
            items.append(
                AdminModelConfigResponse.ModelItem(
                    name=name,
                    label=_first_non_blank(_string_value(item.get("label")), name),
                    kind=kind,
                    provider=profile.provider,
                    vendor=_string_value(item.get("vendor")),
                    family=_string_value(item.get("family")),
                    description=_string_value(item.get("description")),
                    supports_seed=_bool_value(str(item.get("supportsSeed", ""))),
                    supports_responses_api=False,
                    generation_mode=_string_value(item.get("generationMode")),
                    supported_sizes=_parse_string_list(item.get("supportedSizes")),
                    supported_durations=_parse_integer_list(item.get("supportedDurations")),
                    ready=not issues and profile.ready,
                    config_source=profile.source,
                    endpoint_host=profile.endpoint_host,
                    task_endpoint_host=profile.task_endpoint_host,
                    issues=issues,
                )
            )
        return items

    def _read_providers(
        self, models: list[AdminModelConfigResponse.ModelItem]
    ) -> list[AdminModelConfigResponse.ProviderItem]:
        vendor_models: dict[str, list[AdminModelConfigResponse.ModelItem]] = OrderedDict()
        for model in models:
            vendor_key = self._provider_group_key(model.vendor, model.provider)
            vendor_models.setdefault(vendor_key, []).append(model)

        items: list[AdminModelConfigResponse.ProviderItem] = []
        for entry_key, provider_models in vendor_models.items():
            vendor_name = _first_non_blank(
                *[m.vendor for m in provider_models if m.vendor],
                entry_key,
            )
            base_url = self._resolve_provider_base_url(provider_models)
            task_base_url = self._resolve_provider_task_base_url(provider_models)
            items.append(
                AdminModelConfigResponse.ProviderItem(
                    key=entry_key,
                    provider=vendor_name,
                    vendor=vendor_name,
                    kinds=list(OrderedDict.fromkeys(m.kind for m in provider_models).keys()),
                    base_url=base_url,
                    task_base_url=task_base_url,
                    endpoint_host=_host_of(base_url),
                    task_endpoint_host=_host_of(task_base_url),
                    api_key_configured=any(self._resolve_api_key(m) for m in provider_models),
                    base_url_configured=bool(base_url),
                    task_base_url_configured=bool(task_base_url),
                    extras={},
                    model_names=[m.name for m in provider_models],
                )
            )

        items.sort(key=lambda p: p.key.lower())
        return items

    def _resolve_api_key(self, model: AdminModelConfigResponse.ModelItem) -> str:
        if model is None:
            return ""
        if model.kind == GenerationModelKinds.TEXT:
            return self._model_resolver.resolve_text_profile(model.name).api_key
        return self._model_resolver.resolve_media_profile(model.name, model.kind).api_key

    def _resolve_model_base_url(self, model: AdminModelConfigResponse.ModelItem) -> str:
        if model is None:
            return ""
        if model.kind == GenerationModelKinds.TEXT:
            return self._model_resolver.resolve_text_profile(model.name).base_url
        return self._model_resolver.resolve_media_profile(model.name, model.kind).base_url

    def _resolve_provider_base_url(self, provider_models: list[AdminModelConfigResponse.ModelItem]) -> str:
        for m in provider_models:
            b = self._resolve_model_base_url(m)
            if b:
                return b
        return ""

    def _resolve_task_base_url(self, model: AdminModelConfigResponse.ModelItem) -> str:
        if model is None:
            return ""
        return self._model_resolver.resolve_media_profile(model.name, model.kind).task_base_url

    def _resolve_provider_task_base_url(self, provider_models: list[AdminModelConfigResponse.ModelItem]) -> str:
        for m in provider_models:
            if m.kind != GenerationModelKinds.VIDEO:
                continue
            tb = self._resolve_task_base_url(m)
            if tb:
                return tb
            configured = self._model_resolver.value(f"model.providers.{m.provider}.extras", "task_base_url", "")
            if configured:
                return configured
        return ""


# ---------------------------------------------------------------------------
# AdminModelConfigSecretsService (interface placeholder)
# ---------------------------------------------------------------------------


# =============================================================================
# SECRETS SERVICE — encrypted secret storage
# =============================================================================
class AdminModelConfigSecretsService:
    """Interface for saving admin API key secrets."""

    def save_api_keys(self, api_keys: dict[str, str]) -> None:
        raise NotImplementedError


class LocalAdminModelConfigSecretsService(AdminModelConfigSecretsService):
    """Persist platform API keys into config/model/providers.secrets.yml."""

    def __init__(self, config_dir: str | Path = "./config") -> None:
        self._config_dir = Path(config_dir)

    def save_api_keys(self, api_keys: dict[str, str]) -> None:
        if not api_keys:
            return
        path = self._config_dir / "model" / "providers.secrets.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        root: dict[str, Any] = {}
        if path.exists():
            with open(path) as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                root = loaded

        model = root.setdefault("model", {})
        if not isinstance(model, dict):
            model = {}
            root["model"] = model
        providers = model.setdefault("providers", {})
        if not isinstance(providers, dict):
            providers = {}
            model["providers"] = providers

        for provider, api_key in api_keys.items():
            provider_key = _normalize(provider)
            if not provider_key or not api_key:
                continue
            section = providers.setdefault(provider_key, {})
            if not isinstance(section, dict):
                section = {}
                providers[provider_key] = section
            section["api_key"] = api_key

        with open(path, "w") as f:
            yaml.safe_dump(root, f, allow_unicode=True, sort_keys=False)


# =============================================================================
# USER CONFIG — per-user model configuration and API keys
# =============================================================================
