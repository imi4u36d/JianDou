"""Runtime model profile facade over cached snapshots and focused resolvers."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_credentials import RuntimeModelCredentialProvider
from backend.services.model_config_profiles import MediaProviderProfile, ModelRuntimeProfile, ResolvedModel
from backend.services.model_config_runtime_credentials import RuntimeCredentialResolver
from backend.services.model_config_runtime_media import (
    empty_media_runtime_profile,
    resolve_media_runtime_profile,
)
from backend.services.model_config_runtime_snapshot import ModelConfigSnapshotLoader
from backend.services.model_config_runtime_text import resolve_text_runtime_profile
from backend.services.model_config_snapshot import ConfigSection, ConfigSnapshot
from backend.services.model_config_snapshot import normalize_map as _normalize_map
from backend.services.model_config_snapshot import string_value as _string_value
from backend.services.model_config_values import bool_value as _bool_value
from backend.services.model_config_values import (
    configured_provider_model,
    derive_base_url_from_host,
    first_non_blank,
    int_value,
    normalize_base_url,
    resolve_configured_model_section,
    resolve_text_supports_responses_api,
    resolve_watermark_default,
    trim_to_empty,
)


class ModelRuntimePropertiesResolver:
    """Expose the stable runtime configuration API and own snapshot caching."""

    def __init__(
        self,
        config_dir: str | Path = "./config",
        credential_provider: RuntimeModelCredentialProvider | None = None,
    ):
        self._snapshot_loader = ModelConfigSnapshotLoader(config_dir)
        self._credential_resolver = RuntimeCredentialResolver(credential_provider)

    def resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> ModelRuntimeProfile:
        return resolve_text_runtime_profile(
            self._snapshot(),
            self._credential_resolver,
            requested_model,
            user_id,
        )

    def resolve_image_profile(self, requested_model: str, user_id: int | None = None) -> MediaProviderProfile:
        return self._resolve_media_profile(requested_model, GenerationModelKinds.IMAGE, user_id=user_id)

    def resolve_video_profile(self, requested_model: str, user_id: int | None = None) -> MediaProviderProfile:
        return self._resolve_media_profile(requested_model, GenerationModelKinds.VIDEO, user_id=user_id)

    def resolve_media_profile(
        self,
        requested_model: str,
        expected_kind: str | None = None,
        user_id: int | None = None,
    ) -> MediaProviderProfile:
        current = self._snapshot()
        model_name = trim_to_empty(requested_model)
        if expected_kind is None:
            resolved = self._resolve_configured_model(current, model_name)
            expected_kind = first_non_blank(_string_value(resolved.section.get("kind")), "").lower()
        return self._resolve_media_profile(model_name, expected_kind, current, user_id)

    def list_models_by_kind(self, kind: str) -> list[dict[str, Any]]:
        target_kind = trim_to_empty(kind).lower()
        if not target_kind:
            return []
        current = self._snapshot()
        models = current.map("model.models")
        if not models:
            return []
        items: list[dict[str, Any]] = []
        for model_key, model_value in models.items():
            if not isinstance(model_value, dict):
                continue
            section = _normalize_map(model_value)
            if target_kind != trim_to_empty(_string_value(section.get("kind"))).lower():
                continue
            item: dict[str, Any] = OrderedDict()
            item["value"] = model_key
            item["label"] = first_non_blank(_string_value(section.get("label")), model_key)
            provider = trim_to_empty(_string_value(section.get("provider")))
            provider_section = f"model.providers.{provider}" if provider else ""
            item["provider"] = provider
            item["vendor"] = first_non_blank(
                trim_to_empty(_string_value(section.get("vendor"))),
                current.value(provider_section, "vendor") if provider_section else "",
            )
            item["family"] = trim_to_empty(_string_value(section.get("family")))
            item["description"] = trim_to_empty(_string_value(section.get("description")))
            item["kind"] = target_kind

            if target_kind == GenerationModelKinds.TEXT:
                text_profile = self.resolve_text_profile(model_key)
                item["supportsSeed"] = text_profile.supports_seed()
                item["supportsResponsesApi"] = text_profile.supports_responses_api()
                items.append(item)
                continue

            if target_kind in (GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO):
                media_profile = self._resolve_media_profile(model_key, target_kind, current, None)
                item["supportsSeed"] = media_profile.supports_seed()
                if target_kind == GenerationModelKinds.VIDEO:
                    item["generationMode"] = first_non_blank(media_profile.generation_mode(), "i2v")
                item["supportedSizes"] = media_profile.supported_sizes()
                item["supportedDurations"] = media_profile.supported_durations()
            items.append(item)
        return items

    def supports_seed(self, requested_model: str) -> bool:
        model_name = trim_to_empty(requested_model)
        if not model_name:
            return False
        resolved = self._resolve_configured_model(self._snapshot(), model_name)
        return _bool_value(_string_value(resolved.section.get("supports_seed")))

    def config_source(self) -> str:
        return self._snapshot().source

    def config_errors(self) -> list[str]:
        return list(self._snapshot().errors)

    def refresh(self) -> None:
        self._snapshot_loader.refresh()

    def value(self, section: str, key: str, fallback: str = "") -> str:
        return first_non_blank(self._snapshot().value(section, key), fallback)

    def int_value(self, section: str, key: str, fallback: int) -> int:
        return int_value(self._snapshot().value(section, key), fallback)

    def list_sections(self, prefix: str) -> list[ConfigSection]:
        return self._snapshot().list_sections(prefix)

    def section(self, section_name: str) -> dict[str, str]:
        return self._snapshot().section(section_name)

    def _snapshot(self) -> ConfigSnapshot:
        return self._snapshot_loader.snapshot()

    @staticmethod
    def _derive_base_url_from_host(host: str) -> str:
        return derive_base_url_from_host(host)

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        return normalize_base_url(raw)

    @staticmethod
    def _resolve_text_supports_responses_api(
        current: ConfigSnapshot,
        provider_section: str,
        provider: str,
        base_url: str,
    ) -> bool:
        return resolve_text_supports_responses_api(current, provider_section, provider, base_url)

    @staticmethod
    def _resolve_configured_model(current: ConfigSnapshot, requested_model: str) -> ResolvedModel:
        model_name, section = resolve_configured_model_section(current, requested_model)
        return ResolvedModel(model_name, section)

    @staticmethod
    def _configured_provider_model(requested_model: str, resolved: ResolvedModel) -> str:
        return configured_provider_model(requested_model, resolved.canonical_name, resolved.section)

    def _resolve_media_profile(
        self,
        requested_model: str,
        expected_kind: str,
        current: ConfigSnapshot | None = None,
        user_id: int | None = None,
    ) -> MediaProviderProfile:
        return resolve_media_runtime_profile(
            current or self._snapshot(),
            self._credential_resolver,
            requested_model,
            expected_kind,
            user_id,
        )

    @staticmethod
    def _empty_media_profile(kind: str, timeout_seconds: int, source: str) -> MediaProviderProfile:
        return empty_media_runtime_profile(kind, timeout_seconds, source)

    @staticmethod
    def _resolve_watermark_default(kind: str, configured_watermark: str) -> bool:
        return resolve_watermark_default(kind, configured_watermark)
