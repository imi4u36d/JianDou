"""Shared response assembly for admin and per-user model configuration services."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_contracts import (
    AdminModelConfigKeyUpdateRequest,
    AdminModelConfigResponse,
    ApiKeyUpdateBatch,
)
from backend.services.model_config_values import first_non_blank, normalize, trim_to_empty


class ModelConfigResponseSupport:
    """Pure response transformations shared by both model-config services."""

    KIND_ORDER = [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO]
    MISSING_API_KEY_ISSUE = "缺少 api_key"
    _model_resolver: Any

    def _build_provider_key_lookup(
        self, providers: list[AdminModelConfigResponse.ProviderItem]
    ) -> dict[str, str]:
        known: dict[str, str] = OrderedDict()
        for provider in providers:
            known[normalize(provider.key)] = provider.key
            if provider.provider:
                known.setdefault(normalize(provider.provider), provider.key)
            if provider.vendor:
                known.setdefault(normalize(provider.vendor), provider.key)
        for section in self._model_resolver.list_sections("model.providers"):
            vendor_key = self._provider_group_key(
                section.values.get("vendor"),
                first_non_blank(section.values.get("provider"), section.name),
            )
            resolved = known.get(normalize(vendor_key))
            if resolved is None:
                continue
            known.setdefault(normalize(section.name), resolved)
            provider_value = first_non_blank(section.values.get("provider"))
            if provider_value:
                known.setdefault(normalize(provider_value), resolved)
        return known

    def _collect_api_key_updates(
        self,
        request: AdminModelConfigKeyUpdateRequest | None,
        providers: list[AdminModelConfigResponse.ProviderItem],
    ) -> ApiKeyUpdateBatch:
        known = self._build_provider_key_lookup(providers)
        errors: list[str] = []
        updates: dict[str, str] = OrderedDict()
        seen: set[str] = set()
        inputs = request.providers if request and request.providers else []

        for item in inputs:
            requested_key = trim_to_empty(item.key)
            api_key = trim_to_empty(item.apiKey)
            if not requested_key:
                if api_key:
                    errors.append("存在未命名模型接入")
                continue
            resolved = known.get(normalize(requested_key))
            if resolved is None:
                if api_key:
                    errors.append(f"未知模型接入: {requested_key}")
                continue
            if resolved in seen:
                errors.append(f"模型接入重复: {resolved}")
                continue
            seen.add(resolved)
            if api_key:
                updates[resolved] = api_key
        return ApiKeyUpdateBatch(api_keys=dict(updates), errors=errors)

    def _apply_api_key_overrides(
        self,
        base: AdminModelConfigResponse,
        updates: ApiKeyUpdateBatch,
    ) -> AdminModelConfigResponse:
        providers_by_lookup: dict[str, AdminModelConfigResponse.ProviderItem] = OrderedDict()
        providers: list[AdminModelConfigResponse.ProviderItem] = []
        for provider in base.providers:
            updated = AdminModelConfigResponse.ProviderItem(
                key=provider.key,
                provider=provider.provider,
                vendor=provider.vendor,
                kinds=provider.kinds,
                base_url=provider.base_url,
                task_base_url=provider.task_base_url,
                endpoint_host=provider.endpoint_host,
                task_endpoint_host=provider.task_endpoint_host,
                api_key_configured=provider.api_key_configured or provider.key in updates.api_keys,
                base_url_configured=provider.base_url_configured,
                task_base_url_configured=provider.task_base_url_configured,
                extras=provider.extras,
                model_names=provider.model_names,
            )
            providers.append(updated)
            providers_by_lookup[normalize(updated.key)] = updated
            if updated.vendor:
                providers_by_lookup.setdefault(normalize(updated.vendor), updated)
            if updated.provider:
                providers_by_lookup.setdefault(normalize(updated.provider), updated)

        models = [
            self._apply_model_api_key_override(
                model,
                providers_by_lookup.get(first_non_blank(normalize(model.vendor), normalize(model.provider))),
            )
            for model in base.models
        ]
        config_errors = list(base.config_errors)
        config_errors.extend(error for error in updates.errors if error not in config_errors)
        return AdminModelConfigResponse(
            config_source=base.config_source,
            summary=self._build_summary(models, providers),
            defaults=base.defaults,
            providers=providers,
            models=models,
            config_errors=config_errors,
        )

    def _apply_model_api_key_override(
        self,
        model: AdminModelConfigResponse.ModelItem,
        provider: AdminModelConfigResponse.ProviderItem | None,
    ) -> AdminModelConfigResponse.ModelItem:
        missing = self.MISSING_API_KEY_ISSUE in model.issues if provider is None else not provider.api_key_configured
        issues = [self.MISSING_API_KEY_ISSUE] if missing else []
        issues.extend(issue for issue in model.issues if issue != self.MISSING_API_KEY_ISSUE and issue not in issues)
        return AdminModelConfigResponse.ModelItem(
            name=model.name,
            label=model.label,
            kind=model.kind,
            provider=model.provider,
            vendor=model.vendor,
            family=model.family,
            description=model.description,
            supports_seed=model.supports_seed,
            supports_responses_api=model.supports_responses_api,
            generation_mode=model.generation_mode,
            supported_sizes=list(model.supported_sizes),
            supported_durations=list(model.supported_durations),
            ready=not issues,
            config_source=model.config_source,
            endpoint_host=model.endpoint_host,
            task_endpoint_host=model.task_endpoint_host,
            issues=issues,
        )

    def _build_summary(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        providers: list[AdminModelConfigResponse.ProviderItem],
    ) -> AdminModelConfigResponse.Summary:
        return AdminModelConfigResponse.Summary(
            provider_count=len(providers),
            vendor_count=len({normalize(provider.vendor) for provider in providers if provider.vendor}),
            model_count=len(models),
            ready_count=self._count_ready_models(models, None),
            text_ready_count=self._count_ready_models(models, GenerationModelKinds.TEXT),
            image_ready_count=self._count_ready_models(models, GenerationModelKinds.IMAGE),
            video_ready_count=self._count_ready_models(models, GenerationModelKinds.VIDEO),
        )

    @staticmethod
    def _count_ready_models(models: list[AdminModelConfigResponse.ModelItem], kind: str | None) -> int:
        return sum(1 for model in models if model.ready and (kind is None or model.kind == kind))

    def _kind_index(self, kind: str) -> int:
        try:
            return self.KIND_ORDER.index(normalize(kind))
        except ValueError:
            return len(self.KIND_ORDER)

    @staticmethod
    def _provider_group_key(vendor: str | None, fallback: str | None) -> str:
        return first_non_blank(normalize(vendor), normalize(fallback))
