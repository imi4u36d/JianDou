"""Model configuration service - translated from Java.

Provides:
- ModelRuntimePropertiesResolver: Loads YAML model config, resolves runtime profiles.
- AdminModelConfigService: Admin CRUD for model config (API keys).
- UserModelConfigService: Per-user model config (API keys).
"""

from __future__ import annotations

import json
import os
import time
from base64 import urlsafe_b64encode
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

import yaml
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.config import settings
from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_snapshot import (
    ConfigSection,
    ConfigSnapshot,
    merge_maps,
    normalize_map,
    string_value,
)
from backend.services.model_config_values import (
    bool_value,
    configured_provider_model,
    derive_base_url_from_host,
    double_value,
    first_non_blank,
    first_valid_secret,
    host_of,
    int_value,
    normalize,
    normalize_base_url,
    parse_integer_list,
    parse_string_list,
    resolve_configured_model_section,
    resolve_text_supports_responses_api,
    resolve_watermark_default,
    trim_to_empty,
)

# ---------------------------------------------------------------------------
# Utility helpers (mirroring Java private helpers)
# ---------------------------------------------------------------------------

def _trim_to_empty(value: str | None) -> str:
    return trim_to_empty(value)


def _normalize(value: str | None) -> str:
    return normalize(value)


def _string_value(value: object) -> str:
    return string_value(value)


def _first_non_blank(*values: str | None) -> str:
    return first_non_blank(*values)


def _first_valid_secret(*values: str | None) -> str:
    return first_valid_secret(*values)


_FERNET_PREFIX = "fernet:"


def _credential_fernet() -> Fernet:
    key_material = sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(key_material))


def _protect_user_api_key(api_key: str) -> str:
    secret = _first_valid_secret(api_key)
    if not secret:
        return ""
    token = _credential_fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{_FERNET_PREFIX}{token}"


def _unprotect_user_api_key(stored_value: str) -> str:
    value = _trim_to_empty(stored_value)
    if not value:
        return ""
    if not value.startswith(_FERNET_PREFIX):
        return _first_valid_secret(value)
    token = value[len(_FERNET_PREFIX):]
    try:
        decrypted = _credential_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        return ""
    return _first_valid_secret(decrypted)


def _int_value(raw: str, fallback: int) -> int:
    return int_value(raw, fallback)


def _double_value(raw: str, fallback: float) -> float:
    return double_value(raw, fallback)


def _bool_value(raw: str) -> bool:
    return bool_value(raw)


def _normalize_map(source: dict[Any, Any]) -> dict[str, Any]:
    return normalize_map(source)


def _parse_string_list(raw: object) -> list[str]:
    return parse_string_list(raw)


def _parse_integer_list(raw: object) -> list[int]:
    return parse_integer_list(raw)


# ---------------------------------------------------------------------------
# Environment variable helpers
# ---------------------------------------------------------------------------

def _env(key: str) -> str:
    return os.environ.get(key, "").strip()


def _scoped_property(scope: str | None, suffix: str) -> str:
    ns = _trim_to_empty(scope)
    if not ns:
        return ""
    import re
    normalized = re.sub(r"[^A-Z0-9]+", "_", ns.upper())
    return _env(f"JIANDOU_MODEL_{normalized}_{suffix}")


def _provider_property(provider: str, suffix: str) -> str:
    return _scoped_property(provider, suffix)


def _vendor_property(vendor: str, suffix: str) -> str:
    return _scoped_property(vendor, suffix)


# ---------------------------------------------------------------------------
# ResolvedModel
# ---------------------------------------------------------------------------

@dataclass
# =============================================================================
# TYPE DEFINITIONS — provider profiles, capabilities, and value objects
# =============================================================================
class ResolvedModel:
    canonical_name: str
    section: dict[str, Any]

    def section_path(self) -> str:
        if not self.canonical_name:
            return ""
        return f'model.models."{self.canonical_name}"'


# ---------------------------------------------------------------------------
# Text / Media provider config and capability DTOs
# ---------------------------------------------------------------------------

@dataclass
class TextProviderConfig:
    kind: str
    model: str
    provider: str
    provider_model: str
    api_key: str
    base_url: str
    timeout_seconds: int
    temperature: float
    max_tokens: int
    source: str


@dataclass
class TextProviderCapabilities:
    supports_seed: bool
    supports_responses_api: bool


@dataclass
class ModelRuntimeProfile:
    config: TextProviderConfig
    capabilities: TextProviderCapabilities

    @property
    def api_key(self) -> str:
        return self.config.api_key

    @property
    def base_url(self) -> str:
        return self.config.base_url

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def source(self) -> str:
        return self.config.source

    @property
    def endpoint_host(self) -> str:
        return _host_of(self.config.base_url)

    @property
    def ready(self) -> bool:
        return bool(self.config.api_key) and bool(self.config.base_url)

    def supports_seed(self) -> bool:
        return self.capabilities.supports_seed

    def supports_responses_api(self) -> bool:
        return self.capabilities.supports_responses_api


@dataclass
class MediaProviderConfig:
    kind: str
    model: str
    provider: str
    provider_model: str
    api_key: str
    base_url: str
    task_base_url: str
    timeout_seconds: int
    source: str


@dataclass
class MediaProviderCapabilities:
    supports_seed: bool
    prompt_extend: bool
    camera_fixed: bool
    watermark: bool
    poll_interval_seconds: int
    poll_timeout_seconds: int
    generation_mode: str
    supported_sizes: list[str]
    supported_durations: list[int]
    supports_image_data_uri_references: bool


@dataclass
class MediaProviderProfile:
    config: MediaProviderConfig
    capabilities: MediaProviderCapabilities

    @property
    def api_key(self) -> str:
        return self.config.api_key

    @property
    def base_url(self) -> str:
        return self.config.base_url

    @property
    def task_base_url(self) -> str:
        return self.config.task_base_url

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def source(self) -> str:
        return self.config.source

    @property
    def endpoint_host(self) -> str:
        return _host_of(self.config.base_url)

    @property
    def task_endpoint_host(self) -> str:
        return _host_of(self.config.task_base_url)

    @property
    def ready(self) -> bool:
        return bool(self.config.api_key) and bool(self.config.base_url)

    def supports_seed(self) -> bool:
        return self.capabilities.supports_seed

    def generation_mode(self) -> str:
        return self.capabilities.generation_mode

    def supported_sizes(self) -> list[str]:
        return self.capabilities.supported_sizes

    def supported_durations(self) -> list[int]:
        return self.capabilities.supported_durations


def _host_of(raw: str) -> str:
    return host_of(raw)


# ---------------------------------------------------------------------------
# ModelRuntimePropertiesResolver
# ---------------------------------------------------------------------------

# =============================================================================
# CONFIG RESOLVER — loads YAML model config, resolves runtime profiles
# =============================================================================
class ModelRuntimePropertiesResolver:
    """Resolves model runtime properties from YAML config files.

    Mirrors the Java ModelRuntimePropertiesResolver, including:
    - Environment variable overrides
    - User-scoped API key resolution via credential provider
    - Caching of parsed config
    - Text, image, and video profile resolution
    """

    def __init__(
        self,
        config_dir: str | Path = "./config",
        credential_provider: RuntimeModelCredentialProvider | None = None,
    ):
        self._config_dir = Path(config_dir)
        self._credential_provider = credential_provider
        self._cache_ttl_ms: int = self._resolve_cache_ttl()
        self._fail_fast: bool = self._resolve_fail_fast()
        self._cached_snapshot: tuple[ConfigSnapshot, float] | None = None

    # ---- Public API -------------------------------------------------------

    def resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> ModelRuntimeProfile:
        current = self._snapshot()
        user_scoped = user_id is not None
        model_name = _trim_to_empty(requested_model)

        if not model_name:
            return ModelRuntimeProfile(
                TextProviderConfig(
                    kind="",
                    model="",
                    provider="",
                    provider_model="",
                    api_key="",
                    base_url="",
                    timeout_seconds=_int_value(_first_non_blank(current.value("model", "timeout_seconds"), "120"), 120),
                    temperature=_double_value(_first_non_blank(current.value("model", "temperature"), "0.15"), 0.15),
                    max_tokens=_int_value(_first_non_blank(current.value("model", "max_tokens"), "2000"), 2000),
                    source=current.source,
                ),
                TextProviderCapabilities(False, False),
            )

        resolved = self._resolve_configured_model(current, model_name)
        model_section = resolved.section_path()
        model_values = resolved.section
        kind = _first_non_blank(_string_value(model_values.get("kind")), GenerationModelKinds.TEXT).lower()
        provider = _first_non_blank(
            _env("JIANDOU_MODEL_PROVIDER"),
            _string_value(model_values.get("provider")),
            "",
        )
        provider_section = f"model.providers.{provider}"
        vendor = _first_non_blank(_string_value(model_values.get("vendor")), current.value(provider_section, "vendor"))
        user_provider_config = self._resolve_user_provider_config(current, user_id, provider, vendor)
        api_key = self._resolve_api_key(current, user_id, provider, vendor, provider_section)
        base_url = self._normalize_base_url(_first_non_blank(
            user_provider_config.base_url,
            _env("JIANDOU_MODEL_BASE_URL"),
            _env("JIANDOU_MODEL_ENDPOINT"),
            _provider_property(provider, "BASE_URL"),
            _provider_property(provider, "ENDPOINT"),
            current.value(provider_section, "base_url"),
            self._derive_base_url_from_host(_env("JIANDOU_MODEL_ENDPOINT_HOST")),
            "",
        ))
        timeout_seconds = _int_value(
            _first_non_blank(
                user_provider_config.extras.get("timeout_seconds"),
                _env("JIANDOU_MODEL_TIMEOUT"),
                current.value(model_section, "timeout_seconds"),
                current.value(f"{provider_section}.extras", "timeout_seconds"),
                current.value("model", "timeout_seconds"),
                "120",
            ),
            120,
        )
        temperature = _double_value(
            _first_non_blank(
                _env("JIANDOU_MODEL_TEMPERATURE"),
                current.value(model_section, "temperature"),
                current.value("model", "temperature"),
                "0.15",
            ),
            0.15,
        )
        max_tokens = _int_value(
            _first_non_blank(
                _env("JIANDOU_MODEL_MAX_TOKENS"),
                current.value(model_section, "max_tokens"),
                current.value("model", "max_tokens"),
                "2000",
            ),
            2000,
        )
        source = self._resolve_config_source(
            user_scoped, api_key, provider, vendor, current.source,
            bool(_env("JIANDOU_MODEL_PROVIDER")),
        )
        configured_responses_api = _first_non_blank(user_provider_config.extras.get("use_responses_api"))
        supports_responses_api = (
            _bool_value(configured_responses_api)
            if configured_responses_api
            else self._resolve_text_supports_responses_api(current, provider_section, provider, base_url)
        )
        return ModelRuntimeProfile(
            TextProviderConfig(
                kind, model_name, provider,
                self._configured_provider_model(model_name, resolved),
                api_key, base_url, timeout_seconds, temperature, max_tokens, source,
            ),
            TextProviderCapabilities(
                _bool_value(_string_value(model_values.get("supports_seed"))),
                supports_responses_api,
            ),
        )

    def resolve_image_profile(self, requested_model: str, user_id: int | None = None) -> MediaProviderProfile:
        return self._resolve_media_profile(requested_model, GenerationModelKinds.IMAGE, user_id=user_id)

    def resolve_video_profile(self, requested_model: str, user_id: int | None = None) -> MediaProviderProfile:
        return self._resolve_media_profile(requested_model, GenerationModelKinds.VIDEO, user_id=user_id)

    def resolve_media_profile(
        self, requested_model: str, expected_kind: str | None = None, user_id: int | None = None
    ) -> MediaProviderProfile:
        current = self._snapshot()
        model_name = _trim_to_empty(requested_model)

        if expected_kind is None:
            resolved = self._resolve_configured_model(current, model_name)
            kind = _first_non_blank(_string_value(resolved.section.get("kind")), "").lower()
            return self._resolve_media_profile(model_name, kind, current, user_id)

        return self._resolve_media_profile(model_name, expected_kind, current, user_id)

    def list_models_by_kind(self, kind: str) -> list[dict[str, Any]]:
        target_kind = _trim_to_empty(kind).lower()
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
            if target_kind != _trim_to_empty(_string_value(section.get("kind"))).lower():
                continue
            item: dict[str, Any] = OrderedDict()
            item["value"] = model_key
            item["label"] = _first_non_blank(_string_value(section.get("label")), model_key)
            provider = _trim_to_empty(_string_value(section.get("provider")))
            provider_section = f"model.providers.{provider}" if provider else ""
            item["provider"] = provider
            item["vendor"] = _first_non_blank(
                _trim_to_empty(_string_value(section.get("vendor"))),
                current.value(provider_section, "vendor") if provider_section else "",
            )
            item["family"] = _trim_to_empty(_string_value(section.get("family")))
            item["description"] = _trim_to_empty(_string_value(section.get("description")))
            item["kind"] = target_kind

            if target_kind == GenerationModelKinds.TEXT:
                text_profile = self.resolve_text_profile(model_key)
                item["supportsSeed"] = text_profile.supports_seed()
                item["supportsResponsesApi"] = text_profile.supports_responses_api()
                items.append(item)
                continue

            if target_kind in (GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO):
                media_profile = self._resolve_media_profile(model_key, target_kind, current, None)
                item["supportsSeed"] = media_profile.supports_seed() if media_profile else _bool_value(
                    _string_value(section.get("supports_seed"))
                )
                if media_profile:
                    if target_kind == GenerationModelKinds.VIDEO:
                        item["generationMode"] = _first_non_blank(media_profile.generation_mode(), "i2v")
                    item["supportedSizes"] = media_profile.supported_sizes()
                    item["supportedDurations"] = media_profile.supported_durations()
            items.append(item)

        return items

    def supports_seed(self, requested_model: str) -> bool:
        model_name = _trim_to_empty(requested_model)
        if not model_name:
            return False
        resolved = self._resolve_configured_model(self._snapshot(), model_name)
        return _bool_value(_string_value(resolved.section.get("supports_seed")))

    def config_source(self) -> str:
        return self._snapshot().source

    def config_errors(self) -> list[str]:
        return list(self._snapshot().errors)

    def refresh(self) -> None:
        self._cached_snapshot = None

    def value(self, section: str, key: str, fallback: str = "") -> str:
        return _first_non_blank(self._snapshot().value(section, key), fallback)

    def int_value(self, section: str, key: str, fallback: int) -> int:
        return _int_value(self._snapshot().value(section, key), fallback)

    def list_sections(self, prefix: str) -> list[ConfigSection]:
        return self._snapshot().list_sections(prefix)

    def section(self, section_name: str) -> dict[str, str]:
        return self._snapshot().section(section_name)

    # ---- Private helpers --------------------------------------------------

    def _snapshot(self) -> ConfigSnapshot:
        now = time.time() * 1000
        cached = self._cached_snapshot
        if cached is not None and self._cache_valid(cached, now):
            return cached[0]
        loaded = self._load_snapshot()
        self._cached_snapshot = (loaded, now)
        return loaded

    def _cache_valid(self, cached: tuple[ConfigSnapshot, float], now: float) -> bool:
        if not self._cache_enabled():
            return False
        return (now - cached[1]) < self._cache_ttl_ms

    def _cache_enabled(self) -> bool:
        return self._cache_ttl_ms > 0

    def _load_snapshot(self) -> ConfigSnapshot:
        # Primary config locations (project structure: config/model/)
        model_dir = self._config_dir / "model"
        models_yml = model_dir / "models.yml"
        providers_dir = model_dir / "providers"
        secrets_yml = model_dir / "providers.secrets.yml"

        # Legacy fallback locations (Java-style: config/app/, config/secrets/)
        legacy_config_path = self._config_dir / "app" / "models.yml"
        legacy_secrets_path = self._config_dir / "secrets" / "models.yml"

        files_to_load: list[Path] = []
        source_parts: list[str] = []

        # Load model definitions
        if models_yml.exists():
            files_to_load.append(models_yml)
            source_parts.append(f"file:{models_yml.resolve()}")
        elif legacy_config_path.exists():
            files_to_load.append(legacy_config_path)
            source_parts.append(f"file:{legacy_config_path.resolve()}")

        # Load provider configs
        if providers_dir.exists() and providers_dir.is_dir():
            for provider_file in sorted(providers_dir.iterdir()):
                if provider_file.is_file() and provider_file.suffix in (".yml", ".yaml"):
                    if ".secrets." not in provider_file.name:
                        files_to_load.append(provider_file)
                        source_parts.append(f"file:{provider_file.resolve()}")

        # Load secrets (overlay)
        if secrets_yml.exists():
            files_to_load.append(secrets_yml)
            source_parts.append(f"file:{secrets_yml.resolve()}")
        elif legacy_secrets_path.exists():
            files_to_load.append(legacy_secrets_path)
            source_parts.append(f"file:{legacy_secrets_path.resolve()}")

        if not files_to_load:
            msg = f"Generation config directory missing: {self._config_dir}"
            return self._fail_or_snapshot({}, msg, None)

        source = " + ".join(source_parts)
        try:
            root: dict[str, Any] = {}
            for fp in files_to_load:
                with open(fp) as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    root = merge_maps(root, _normalize_map(data))
            return ConfigSnapshot(root, source, [])
        except Exception as ex:
            msg = f"Failed to load generation config from {source}: {ex}"
            return self._fail_or_snapshot({}, f"error:{source}", ex)

    def _fail_or_snapshot(
        self, root: dict[str, Any], source: str, exc: Exception | None
    ) -> ConfigSnapshot:
        if self._fail_fast:
            msg = f"Generation configuration error (source={source})"
            if exc:
                msg += f" (cause={exc.__class__.__name__})"
            raise RuntimeError(msg)
        err = f"Failed to load generation config from {source}" + (f": {exc}" if exc else "")
        return ConfigSnapshot(root, source, [err])

    def _resolve_api_key(
        self,
        current: ConfigSnapshot,
        user_id: int | None,
        provider: str,
        vendor: str,
        provider_section: str,
    ) -> str:
        if user_id is not None:
            return self._resolve_user_api_key(current, user_id, provider, vendor)
        return _first_valid_secret(
            _env("JIANDOU_MODEL_API_KEY"),
            _provider_property(provider, "API_KEY"),
            _vendor_property(vendor, "API_KEY"),
            current.value(f"model.providers.{vendor}", "api_key") if vendor else "",
            current.value(provider_section, "api_key"),
            self._resolve_shared_configured_api_key(current, provider, vendor),
            "",
        )

    def _resolve_user_api_key(
        self, current: ConfigSnapshot, user_id: int, provider: str, vendor: str
    ) -> str:
        if self._credential_provider is None:
            return ""
        return _first_valid_secret(
            self._credential_provider.find_runtime_api_key(
                user_id, self._preferred_api_key_scopes(current, provider, vendor)
            )
        )

    def _resolve_user_provider_config(
        self, current: ConfigSnapshot, user_id: int | None, provider: str, vendor: str
    ) -> RuntimeProviderConfig:
        if user_id is None or self._credential_provider is None:
            return RuntimeProviderConfig()
        return self._credential_provider.find_runtime_provider_config(
            user_id, self._preferred_api_key_scopes(current, provider, vendor)
        )

    def _preferred_api_key_scopes(
        self, current: ConfigSnapshot, provider: str, vendor: str
    ) -> list[str]:
        # Check provider first (most specific), then siblings, and finally vendor as the broadest fallback.
        # This ensures that a key saved under any sibling or vendor name can still be resolved,
        # while preserving the preference for a more specific provider-level key when it exists.
        scopes: list[str] = []
        self._add_api_key_scope(scopes, provider)
        for sibling in self._same_vendor_provider_keys(current, provider, vendor):
            self._add_api_key_scope(scopes, sibling)
        self._add_api_key_scope(scopes, vendor)
        return scopes

    def _resolve_shared_configured_api_key(
        self, current: ConfigSnapshot, provider: str, vendor: str
    ) -> str:
        for sibling in self._same_vendor_provider_keys(current, provider, vendor):
            ak = current.value(f"model.providers.{sibling}", "api_key")
            if _first_valid_secret(ak):
                return ak
        return ""

    def _same_vendor_provider_keys(
        self, current: ConfigSnapshot, provider: str, vendor: str
    ) -> list[str]:
        nv = _normalize(vendor)
        if not nv:
            return []
        keys: list[str] = []
        for section in current.list_sections("model.providers"):
            section_vendor = _first_non_blank(section.values.get("vendor"))
            if nv != _normalize(section_vendor):
                continue
            self._add_api_key_scope(keys, section.name)
            self._add_api_key_scope(keys, section.values.get("provider"))
        keys = [k for k in keys if _normalize(k) != _normalize(provider)]
        return keys

    @staticmethod
    def _add_api_key_scope(scopes: list[str], candidate: str) -> None:
        nc = _trim_to_empty(candidate)
        if nc and not any(_normalize(s) == _normalize(nc) for s in scopes):
            scopes.append(nc)

    @staticmethod
    def _resolve_config_source(
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
            _env("JIANDOU_MODEL_API_KEY")
            or _provider_property(provider, "API_KEY")
            or _vendor_property(vendor, "API_KEY")
            or _env("JIANDOU_MODEL_BASE_URL")
            or _provider_property(provider, "BASE_URL")
            or _provider_property(provider, "TASK_BASE_URL")
            or provider_overridden
        ):
            return "env"
        return default_source

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

    @staticmethod
    def _resolve_cache_ttl() -> int:
        seconds = _int_value(
            _first_non_blank(
                _env("JIANDOU_CONFIG_CACHE_TTL_SECONDS"),
                _env("JIANDOU_CONFIG_REFRESH_SECONDS"),
                "5",
            ),
            5,
        )
        seconds = max(0, min(seconds, 3600))
        return seconds * 1000

    @staticmethod
    def _resolve_fail_fast() -> bool:
        model_level = _first_non_blank(
            _env("JIANDOU_MODEL_CONFIG_FAIL_FAST"),
        )
        if model_level:
            return _bool_value(model_level)
        return _bool_value(_first_non_blank(
            _env("JIANDOU_CONFIG_FAIL_FAST"),
            "false",
        ))

    def _resolve_media_profile(
        self,
        requested_model: str,
        expected_kind: str,
        current: ConfigSnapshot | None = None,
        user_id: int | None = None,
    ) -> MediaProviderProfile:
        if current is None:
            current = self._snapshot()

        user_scoped = user_id is not None
        model_name = _trim_to_empty(requested_model)
        normalized_expected_kind = _trim_to_empty(expected_kind).lower()

        if not model_name:
            timeout = _int_value(_first_non_blank(current.value("model", "timeout_seconds"), "120"), 120)
            return self._empty_media_profile(normalized_expected_kind, timeout, current.source)

        resolved = self._resolve_configured_model(current, model_name)
        model_section = resolved.section_path()
        model_values = resolved.section
        actual_kind = _first_non_blank(_string_value(model_values.get("kind")), normalized_expected_kind).lower()
        provider = _first_non_blank(_string_value(model_values.get("provider")), "")
        provider_section = f"model.providers.{provider}"
        vendor = _first_non_blank(_string_value(model_values.get("vendor")), current.value(provider_section, "vendor"))
        vendor_section = f"model.providers.{vendor}" if vendor else ""
        user_provider_config = self._resolve_user_provider_config(current, user_id, provider, vendor)
        base_url = self._normalize_base_url(_first_non_blank(
            user_provider_config.base_url,
            _provider_property(provider, "BASE_URL"),
            _provider_property(provider, "ENDPOINT"),
            current.value(provider_section, "base_url"),
            current.value(vendor_section, "base_url") if vendor_section else "",
        ))
        task_base_url = self._normalize_base_url(_first_non_blank(
            user_provider_config.task_base_url,
            _provider_property(provider, "TASK_BASE_URL"),
            current.value(f"{provider_section}.extras", "task_base_url"),
            current.value(f"{vendor_section}.extras", "task_base_url") if vendor_section else "",
        ))
        api_key = self._resolve_api_key(current, user_id, provider, vendor, provider_section)
        source = self._resolve_config_source(user_scoped, api_key, provider, vendor, current.source, False)

        timeout_seconds = _int_value(
            _first_non_blank(
                user_provider_config.extras.get("timeout_seconds"),
                _provider_property(provider, "TIMEOUT_SECONDS"),
                current.value(model_section, "timeout_seconds"),
                current.value(f"{provider_section}.extras", "timeout_seconds"),
                current.value(f"{vendor_section}.extras", "timeout_seconds") if vendor_section else "",
                current.value("model", "timeout_seconds"),
                "120",
            ),
            120,
        )

        is_video = actual_kind == GenerationModelKinds.VIDEO
        return MediaProviderProfile(
            MediaProviderConfig(
                actual_kind, model_name, provider,
                self._configured_provider_model(model_name, resolved),
                api_key, base_url, task_base_url, timeout_seconds, source,
            ),
            MediaProviderCapabilities(
                supports_seed=_bool_value(_string_value(model_values.get("supports_seed"))),
                prompt_extend=_bool_value(_first_non_blank(
                    user_provider_config.extras.get("prompt_extend"),
                    current.value(f"{provider_section}.extras", "prompt_extend"),
                    current.value(f"{vendor_section}.extras", "prompt_extend") if vendor_section else "",
                )),
                camera_fixed=_bool_value(_first_non_blank(
                    user_provider_config.extras.get("camera_fixed"),
                    current.value(f"{provider_section}.extras", "camera_fixed"),
                    current.value(f"{vendor_section}.extras", "camera_fixed") if vendor_section else "",
                )),
                watermark=self._resolve_watermark_default(actual_kind, _first_non_blank(
                    user_provider_config.extras.get("watermark"),
                    current.value(f"{provider_section}.extras", "watermark"),
                    current.value(f"{vendor_section}.extras", "watermark") if vendor_section else "",
                )),
                poll_interval_seconds=_int_value(
                    _first_non_blank(
                        user_provider_config.extras.get("poll_interval_seconds"),
                        current.value(f"{provider_section}.extras", "poll_interval_seconds"),
                        current.value(f"{vendor_section}.extras", "poll_interval_seconds") if vendor_section else "",
                        "8" if is_video else "5",
                    ),
                    8 if is_video else 5,
                ),
                poll_timeout_seconds=_int_value(
                    _first_non_blank(
                        user_provider_config.extras.get("poll_timeout_seconds"),
                        current.value(f"{provider_section}.extras", "poll_timeout_seconds"),
                        current.value(f"{vendor_section}.extras", "poll_timeout_seconds") if vendor_section else "",
                        "600" if is_video else "120",
                    ),
                    600 if is_video else 120,
                ),
                generation_mode=_first_non_blank(_string_value(model_values.get("generation_mode")), "i2v" if is_video else ""),
                supported_sizes=_parse_string_list(model_values.get("supported_sizes")),
                supported_durations=_parse_integer_list(model_values.get("supported_durations")),
                supports_image_data_uri_references=_bool_value(_string_value(model_values.get("supports_image_data_uri_references"))),
            ),
        )

    @staticmethod
    def _empty_media_profile(kind: str, timeout_seconds: int, source: str) -> MediaProviderProfile:
        is_video = kind == GenerationModelKinds.VIDEO
        return MediaProviderProfile(
            MediaProviderConfig(kind, "", "", "", "", "", "", timeout_seconds, source),
            MediaProviderCapabilities(
                supports_seed=False,
                prompt_extend=False,
                camera_fixed=False,
                watermark=not (kind == GenerationModelKinds.IMAGE),
                poll_interval_seconds=8 if is_video else 5,
                poll_timeout_seconds=600 if is_video else 120,
                generation_mode="i2v" if is_video else "",
                supported_sizes=[],
                supported_durations=[],
                supports_image_data_uri_references=False,
            ),
        )

    @staticmethod
    def _resolve_watermark_default(kind: str, configured_watermark: str) -> bool:
        return resolve_watermark_default(kind, configured_watermark)


# ---------------------------------------------------------------------------
# RuntimeModelCredentialProvider (protocol/interface)
# ---------------------------------------------------------------------------

# =============================================================================
# CREDENTIAL PROVIDER — manages model API keys
# =============================================================================
class RuntimeModelCredentialProvider:
    """Interface for resolving user-scoped API keys."""

    def find_runtime_api_key(self, user_id: int, preferred_scopes: list[str]) -> str:
        raise NotImplementedError

    def find_runtime_provider_config(self, user_id: int, preferred_scopes: list[str]) -> RuntimeProviderConfig:
        return RuntimeProviderConfig()


@dataclass
class RuntimeProviderConfig:
    base_url: str = ""
    task_base_url: str = ""
    extras: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Admin model config response DTOs (simplified)
# ---------------------------------------------------------------------------

@dataclass
class AdminModelConfigKeyUpdateRequest:
    @dataclass
    class ProviderKeyInput:
        key: str
        apiKey: str

    providers: list[ProviderKeyInput] = field(default_factory=list)


@dataclass
class AdminModelConfigResponse:
    @dataclass
    class Defaults:
        default_aspect_ratio: str
        style_preset: str
        image_size: str
        video_size: str
        video_duration_seconds: int
        timeout_seconds: int
        temperature: float
        max_tokens: int

    @dataclass
    class Summary:
        provider_count: int
        vendor_count: int
        model_count: int
        ready_count: int
        text_ready_count: int
        image_ready_count: int
        video_ready_count: int

    @dataclass
    class ModelItem:
        name: str
        label: str
        kind: str
        provider: str
        vendor: str
        family: str
        description: str
        supports_seed: bool
        supports_responses_api: bool
        generation_mode: str
        supported_sizes: list[str]
        supported_durations: list[int]
        ready: bool
        config_source: str
        endpoint_host: str
        task_endpoint_host: str
        issues: list[str]

    @dataclass
    class ProviderItem:
        key: str
        provider: str
        vendor: str
        kinds: list[str]
        base_url: str
        task_base_url: str
        endpoint_host: str
        task_endpoint_host: str
        api_key_configured: bool
        base_url_configured: bool
        task_base_url_configured: bool
        extras: dict[str, str]
        model_names: list[str]

    config_source: str
    summary: AdminModelConfigResponse.Summary
    defaults: AdminModelConfigResponse.Defaults
    providers: list[AdminModelConfigResponse.ProviderItem]
    models: list[AdminModelConfigResponse.ModelItem]
    config_errors: list[str]


@dataclass
class AdminModelConfigValidationResponse:
    valid: bool
    snapshot: AdminModelConfigResponse


# ---------------------------------------------------------------------------
# AdminModelConfigService
# ---------------------------------------------------------------------------

# =============================================================================
# ADMIN SERVICE — CRUD for model configuration
# =============================================================================
class AdminModelConfigService:
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
        valid = (
            not snapshot.config_errors
            and all(m.ready for m in snapshot.models)
        )
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
            style_preset=self._model_resolver.value("catalog.defaults", "style_preset", "cinematic"),
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
            items.append(AdminModelConfigResponse.ModelItem(
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
            ))
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
            items.append(AdminModelConfigResponse.ModelItem(
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
            ))
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
            items.append(AdminModelConfigResponse.ProviderItem(
                key=entry_key,
                provider=vendor_name,
                vendor=vendor_name,
                kinds=list(OrderedDict.fromkeys(m.kind for m in provider_models).keys()),
                base_url=base_url,
                task_base_url=task_base_url,
                endpoint_host=_host_of(base_url),
                task_endpoint_host=_host_of(task_base_url),
                api_key_configured=any(
                    self._resolve_api_key(m) for m in provider_models
                ),
                base_url_configured=bool(base_url),
                task_base_url_configured=bool(task_base_url),
                extras={},
                model_names=[m.name for m in provider_models],
            ))

        items.sort(key=lambda p: p.key.lower())
        return items

    def _build_provider_key_lookup(
        self, providers: list[AdminModelConfigResponse.ProviderItem]
    ) -> dict[str, str]:
        known: dict[str, str] = OrderedDict()
        for p in providers:
            known[_normalize(p.key)] = p.key
            if p.provider:
                known.setdefault(_normalize(p.provider), p.key)
            if p.vendor:
                known.setdefault(_normalize(p.vendor), p.key)
        for section in self._model_resolver.list_sections("model.providers"):
            vendor_key = self._provider_group_key(
                section.values.get("vendor"),
                _first_non_blank(section.values.get("provider"), section.name),
            )
            resolved = known.get(_normalize(vendor_key))
            if resolved is None:
                continue
            known.setdefault(_normalize(section.name), resolved)
            provider_val = _first_non_blank(section.values.get("provider"))
            if provider_val:
                known.setdefault(_normalize(provider_val), resolved)
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

        for inp in inputs:
            requested_key = _trim_to_empty(inp.key)
            api_key = _trim_to_empty(inp.apiKey)

            if not requested_key:
                if api_key:
                    errors.append("存在未命名模型接入")
                continue

            resolved = known.get(_normalize(requested_key))
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

        return ApiKeyUpdateBatch(api_keys=dict(updates), errors=list(errors))

    def _apply_api_key_overrides(
        self,
        base: AdminModelConfigResponse,
        updates: ApiKeyUpdateBatch,
    ) -> AdminModelConfigResponse:
        providers_by_lookup: dict[str, AdminModelConfigResponse.ProviderItem] = OrderedDict()
        providers: list[AdminModelConfigResponse.ProviderItem] = []

        for p in base.providers:
            api_key_configured = p.api_key_configured or p.key in updates.api_keys
            updated = AdminModelConfigResponse.ProviderItem(
                key=p.key, provider=p.provider, vendor=p.vendor,
                kinds=p.kinds, base_url=p.base_url, task_base_url=p.task_base_url,
                endpoint_host=p.endpoint_host, task_endpoint_host=p.task_endpoint_host,
                api_key_configured=api_key_configured,
                base_url_configured=p.base_url_configured,
                task_base_url_configured=p.task_base_url_configured,
                extras=p.extras, model_names=p.model_names,
            )
            providers.append(updated)
            providers_by_lookup[_normalize(updated.key)] = updated
            if updated.vendor:
                providers_by_lookup.setdefault(_normalize(updated.vendor), updated)
            if updated.provider:
                providers_by_lookup.setdefault(_normalize(updated.provider), updated)

        models = [
            self._apply_model_api_key_override(
                m,
                providers_by_lookup.get(
                    _first_non_blank(_normalize(m.vendor), _normalize(m.provider))
                ),
            )
            for m in base.models
        ]

        config_errors = list(base.config_errors)
        for err in updates.errors:
            if err not in config_errors:
                config_errors.append(err)

        return AdminModelConfigResponse(
            config_source=base.config_source,
            summary=self._build_summary(models, providers),
            defaults=base.defaults,
            providers=list(providers),
            models=list(models),
            config_errors=list(config_errors),
        )

    @staticmethod
    def _apply_model_api_key_override(
        model: AdminModelConfigResponse.ModelItem,
        provider: AdminModelConfigResponse.ProviderItem | None,
    ) -> AdminModelConfigResponse.ModelItem:
        issues: list[str] = []
        missing = (
            AdminModelConfigService.MISSING_API_KEY_ISSUE in model.issues
            if provider is None
            else not provider.api_key_configured
        )
        if missing:
            issues.append(AdminModelConfigService.MISSING_API_KEY_ISSUE)
        for issue in model.issues:
            if issue == AdminModelConfigService.MISSING_API_KEY_ISSUE or issue in issues:
                continue
            issues.append(issue)
        return AdminModelConfigResponse.ModelItem(
            name=model.name, label=model.label, kind=model.kind,
            provider=model.provider, vendor=model.vendor, family=model.family,
            description=model.description, supports_seed=model.supports_seed,
            supports_responses_api=model.supports_responses_api,
            generation_mode=model.generation_mode,
            supported_sizes=list(model.supported_sizes),
            supported_durations=list(model.supported_durations),
            ready=not issues, config_source=model.config_source,
            endpoint_host=model.endpoint_host,
            task_endpoint_host=model.task_endpoint_host,
            issues=list(issues),
        )

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

    def _resolve_provider_base_url(
        self, provider_models: list[AdminModelConfigResponse.ModelItem]
    ) -> str:
        for m in provider_models:
            b = self._resolve_model_base_url(m)
            if b:
                return b
        return ""

    def _resolve_task_base_url(self, model: AdminModelConfigResponse.ModelItem) -> str:
        if model is None:
            return ""
        return self._model_resolver.resolve_media_profile(model.name, model.kind).task_base_url

    def _resolve_provider_task_base_url(
        self, provider_models: list[AdminModelConfigResponse.ModelItem]
    ) -> str:
        for m in provider_models:
            if m.kind != GenerationModelKinds.VIDEO:
                continue
            tb = self._resolve_task_base_url(m)
            if tb:
                return tb
            configured = self._model_resolver.value(
                f"model.providers.{m.provider}.extras", "task_base_url", ""
            )
            if configured:
                return configured
        return ""

    def _build_summary(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        providers: list[AdminModelConfigResponse.ProviderItem],
    ) -> AdminModelConfigResponse.Summary:
        provider_count = len(providers) if providers else 0
        vendor_count = len({_normalize(p.vendor) for p in providers if p.vendor}) if providers else 0
        return AdminModelConfigResponse.Summary(
            provider_count=provider_count,
            vendor_count=vendor_count,
            model_count=len(models),
            ready_count=self._count_ready_models(models, None),
            text_ready_count=self._count_ready_models(models, GenerationModelKinds.TEXT),
            image_ready_count=self._count_ready_models(models, GenerationModelKinds.IMAGE),
            video_ready_count=self._count_ready_models(models, GenerationModelKinds.VIDEO),
        )

    @staticmethod
    def _count_ready_models(
        models: list[AdminModelConfigResponse.ModelItem], kind: str | None
    ) -> int:
        return sum(
            1 for m in models
            if m.ready and (kind is None or m.kind == kind)
        )

    def _kind_index(self, kind: str) -> int:
        try:
            return self.KIND_ORDER.index(_normalize(kind))
        except ValueError:
            return len(self.KIND_ORDER)

    @staticmethod
    def _provider_group_key(vendor: str, fallback: str) -> str:
        return _first_non_blank(_normalize(vendor), _normalize(fallback))


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


# ---------------------------------------------------------------------------
# ApiKeyUpdateBatch (internal helper)
# ---------------------------------------------------------------------------

@dataclass
# =============================================================================
# USER CONFIG — per-user model configuration and API keys
# =============================================================================
class ApiKeyUpdateBatch:
    api_keys: dict[str, str]
    errors: list[str]


# ---------------------------------------------------------------------------
# UserModelConfigService
# ---------------------------------------------------------------------------

class UserModelConfigService:
    """Per-user model configuration service.

    Mirrors the Java UserModelConfigService.
    """

    KIND_ORDER = [GenerationModelKinds.TEXT, GenerationModelKinds.IMAGE, GenerationModelKinds.VIDEO]
    MISSING_API_KEY_ISSUE = "缺少 api_key"

    def __init__(
        self,
        model_resolver: ModelRuntimePropertiesResolver,
        user_credential_repo: MybatisUserModelCredentialRepository | None = None,
    ):
        self._model_resolver = model_resolver
        self._user_credential_repo = user_credential_repo

    def read(self, user_id: int) -> AdminModelConfigResponse:
        api_keys: dict[str, str] = {}
        if self._user_credential_repo:
            api_keys = self._user_credential_repo.find_api_keys_by_user_id(user_id)

        models: list[AdminModelConfigResponse.ModelItem] = []
        models.extend(self._read_text_models(GenerationModelKinds.TEXT, user_id))
        models.extend(self._read_media_models(GenerationModelKinds.IMAGE, user_id))
        models.extend(self._read_media_models(GenerationModelKinds.VIDEO, user_id))
        models.sort(key=lambda m: (self._kind_index(m.kind), m.name.lower()))

        providers = self._read_providers(models, api_keys, user_id)
        return AdminModelConfigResponse(
            config_source="user-db",
            summary=self._build_summary(models, providers),
            defaults=self._read_defaults(),
            providers=providers,
            models=list(models),
            config_errors=list(self._model_resolver.config_errors()),
        )

    def validate_keys(self, user_id: int, request: AdminModelConfigKeyUpdateRequest) -> AdminModelConfigValidationResponse:
        current = self.read(user_id)
        snapshot = self._apply_api_key_overrides(current, self._collect_api_key_updates(request, current.providers))
        valid = not snapshot.config_errors and all(m.ready for m in snapshot.models)
        return AdminModelConfigValidationResponse(valid=valid, snapshot=snapshot)

    def save_keys(self, user_id: int, request: AdminModelConfigKeyUpdateRequest) -> AdminModelConfigResponse:
        current = self.read(user_id)
        updates = self._collect_api_key_updates(request, current.providers)
        if updates.errors:
            raise ValueError(" / ".join(updates.errors))
        if updates.api_keys and self._user_credential_repo:
            self._user_credential_repo.save_api_keys(user_id, updates.api_keys)
        return self.read(user_id)

    def reset_keys(self, user_id: int, request: AdminModelConfigKeyUpdateRequest) -> None:
        if user_id is None:
            raise ValueError("缺少用户ID")
        updates = self._collect_api_key_updates(request, self._read_provider_catalog())
        if updates.errors:
            raise ValueError(" / ".join(updates.errors))
        if updates.api_keys and self._user_credential_repo:
            self._user_credential_repo.save_api_keys(user_id, updates.api_keys)

    # ---- Private helpers --------------------------------------------------

    def _read_defaults(self) -> AdminModelConfigResponse.Defaults:
        return AdminModelConfigResponse.Defaults(
            default_aspect_ratio=self._model_resolver.value("pipeline", "default_aspect_ratio", "9:16"),
            style_preset=self._model_resolver.value("catalog.defaults", "style_preset", "cinematic"),
            image_size=self._model_resolver.value("catalog.defaults", "image_size", "1024x1024"),
            video_size=self._model_resolver.value("catalog.defaults", "video_size", "720*1280"),
            video_duration_seconds=self._model_resolver.int_value("catalog.defaults", "video_duration_seconds", 8),
            timeout_seconds=self._model_resolver.int_value("model", "timeout_seconds", 120),
            temperature=_double_value(self._model_resolver.value("model", "temperature", "0.15"), 0.15),
            max_tokens=self._model_resolver.int_value("model", "max_tokens", 2000),
        )

    def _read_text_models(self, kind: str, user_id: int) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_text_profile(name, user_id)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            items.append(AdminModelConfigResponse.ModelItem(
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
            ))
        return items

    def _read_media_models(self, kind: str, user_id: int) -> list[AdminModelConfigResponse.ModelItem]:
        items: list[AdminModelConfigResponse.ModelItem] = []
        for item in self._model_resolver.list_models_by_kind(kind):
            name = _string_value(item.get("value"))
            profile = self._model_resolver.resolve_media_profile(name, kind, user_id)
            issues: list[str] = []
            if not profile.api_key:
                issues.append(self.MISSING_API_KEY_ISSUE)
            if not profile.base_url:
                issues.append("缺少 base_url")
            if kind == GenerationModelKinds.VIDEO and not profile.task_base_url:
                issues.append("缺少 task_base_url")
            items.append(AdminModelConfigResponse.ModelItem(
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
            ))
        return items

    def _read_providers(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        api_keys: dict[str, str],
        user_id: int,
    ) -> list[AdminModelConfigResponse.ProviderItem]:
        vendor_models: dict[str, list[AdminModelConfigResponse.ModelItem]] = OrderedDict()
        for m in models:
            key = self._provider_group_key(m.vendor, m.provider)
            vendor_models.setdefault(key, []).append(m)

        items: list[AdminModelConfigResponse.ProviderItem] = []
        for entry_key, provider_models in vendor_models.items():
            vendor_name = _first_non_blank(
                *[m.vendor for m in provider_models if m.vendor],
                entry_key,
            )
            base_url = self._resolve_provider_base_url(provider_models, user_id)
            task_base_url = self._resolve_provider_task_base_url(provider_models, user_id)
            items.append(AdminModelConfigResponse.ProviderItem(
                key=entry_key, provider=vendor_name, vendor=vendor_name,
                kinds=list(OrderedDict.fromkeys(m.kind for m in provider_models)),
                base_url=base_url, task_base_url=task_base_url,
                endpoint_host=_host_of(base_url),
                task_endpoint_host=_host_of(task_base_url),
                api_key_configured=any(
                    self._is_api_key_configured(m, api_keys, user_id)
                    for m in provider_models
                ),
                base_url_configured=bool(base_url),
                task_base_url_configured=bool(task_base_url),
                extras={},
                model_names=[m.name for m in provider_models],
            ))

        # Also include config-only providers (those without any models) so that
        # API keys saved for them are visible in the response.
        existing_keys = {p.key.lower() for p in items}
        for section in self._model_resolver.list_sections("model.providers"):
            provider_val = _first_non_blank(section.values.get("provider"), section.name)
            vendor_val = _string_value(section.values.get("vendor"))
            entry_key = self._provider_group_key(vendor_val, provider_val)
            if not entry_key or _normalize(entry_key) in existing_keys:
                continue

            vendor_name = _first_non_blank(vendor_val, provider_val, entry_key)
            base_url = self._resolve_provider_base_url_for_config(entry_key, user_id)
            task_base_url = ""
            items.append(AdminModelConfigResponse.ProviderItem(
                key=entry_key, provider=vendor_name, vendor=vendor_name,
                kinds=[], base_url=base_url, task_base_url=task_base_url,
                endpoint_host=_host_of(base_url),
                task_endpoint_host="",
                api_key_configured=self._contains_api_key(api_keys, entry_key)
                                   or self._contains_api_key(api_keys, provider_val),
                base_url_configured=bool(base_url),
                task_base_url_configured=False,
                extras={},
                model_names=[],
            ))
            existing_keys.add(_normalize(entry_key))

        items.sort(key=lambda p: p.key.lower())
        return items

    def _read_provider_catalog(self) -> list[AdminModelConfigResponse.ProviderItem]:
        providers: dict[str, _ProviderCatalogItem] = OrderedDict()
        self._add_provider_catalog_models(providers, GenerationModelKinds.TEXT)
        self._add_provider_catalog_models(providers, GenerationModelKinds.IMAGE)
        self._add_provider_catalog_models(providers, GenerationModelKinds.VIDEO)
        for section in self._model_resolver.list_sections("model.providers"):
            provider = _first_non_blank(section.values.get("provider"), section.name)
            vendor = _string_value(section.values.get("vendor"))
            key = self._provider_group_key(vendor, provider)
            if not key:
                continue
            providers.setdefault(key, _ProviderCatalogItem(key, provider, vendor))
        return sorted(
            (p.to_provider_item() for p in providers.values()),
            key=lambda pi: pi.key.lower(),
        )

    def _add_provider_catalog_models(
        self, providers: dict[str, _ProviderCatalogItem], kind: str
    ) -> None:
        for item in self._model_resolver.list_models_by_kind(kind):
            provider = _string_value(item.get("provider"))
            vendor = _string_value(item.get("vendor"))
            key = self._provider_group_key(vendor, provider)
            if not key:
                key = _string_value(item.get("value"))
            if not key:
                continue
            pi = providers.setdefault(key, _ProviderCatalogItem(key, provider, vendor))
            pi.add_kind(kind)
            pi.add_model_name(_string_value(item.get("value")))

    def _resolve_provider_base_url(
        self,
        provider_models: list[AdminModelConfigResponse.ModelItem],
        user_id: int,
    ) -> str:
        for m in provider_models:
            if m.kind == GenerationModelKinds.TEXT:
                b = self._model_resolver.resolve_text_profile(m.name, user_id).base_url
                if b:
                    return b
                continue
            b = self._model_resolver.resolve_media_profile(m.name, m.kind, user_id).base_url
            if b:
                return b
        return ""

    def _resolve_provider_task_base_url(
        self,
        provider_models: list[AdminModelConfigResponse.ModelItem],
        user_id: int,
    ) -> str:
        for m in provider_models:
            if m.kind != GenerationModelKinds.VIDEO:
                continue
            tb = self._model_resolver.resolve_media_profile(m.name, m.kind, user_id).task_base_url
            if tb:
                return tb
            configured = self._model_resolver.value(
                f"model.providers.{m.provider}.extras", "task_base_url", ""
            )
            if configured:
                return configured
        return ""

    def _resolve_provider_base_url_for_config(
        self, provider_key: str, user_id: int,
    ) -> str:
        """Resolve base_url for a config-only provider section (no models)."""
        # Try resolving via text profile first, then media profiles for each known kind.
        base_url = self._model_resolver.value(f"model.providers.{provider_key}", "base_url", "")
        if base_url:
            return self._normalize_base_url(base_url)
        # Fall back to env or derived URL.
        env_endpoint = os.environ.get("JIANDOU_MODEL_ENDPOINT", "").strip()
        if env_endpoint:
            return self._normalize_base_url(env_endpoint)
        endpoint_host = os.environ.get("JIANDOU_MODEL_ENDPOINT_HOST", "").strip()
        if endpoint_host:
            return self._derive_base_url_from_host(endpoint_host)
        return ""

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        return normalize_base_url(raw)

    @staticmethod
    def _derive_base_url_from_host(host: str) -> str:
        return derive_base_url_from_host(host)

    def _build_provider_key_lookup(
        self, providers: list[AdminModelConfigResponse.ProviderItem]
    ) -> dict[str, str]:
        known: dict[str, str] = OrderedDict()
        for p in providers:
            known[_normalize(p.key)] = p.key
            if p.provider:
                known.setdefault(_normalize(p.provider), p.key)
            if p.vendor:
                known.setdefault(_normalize(p.vendor), p.key)
        for section in self._model_resolver.list_sections("model.providers"):
            vendor_key = self._provider_group_key(
                section.values.get("vendor"),
                _first_non_blank(section.values.get("provider"), section.name),
            )
            resolved = known.get(_normalize(vendor_key))
            if resolved is None:
                continue
            known.setdefault(_normalize(section.name), resolved)
            provider_val = _first_non_blank(section.values.get("provider"))
            if provider_val:
                known.setdefault(_normalize(provider_val), resolved)
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

        for inp in inputs:
            requested_key = _trim_to_empty(inp.key)
            api_key = _trim_to_empty(inp.apiKey)

            if not requested_key:
                if api_key:
                    errors.append("存在未命名模型接入")
                continue

            resolved = known.get(_normalize(requested_key))
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

        return ApiKeyUpdateBatch(api_keys=dict(updates), errors=list(errors))

    def _apply_api_key_overrides(
        self,
        base: AdminModelConfigResponse,
        updates: ApiKeyUpdateBatch,
    ) -> AdminModelConfigResponse:
        providers_by_lookup: dict[str, AdminModelConfigResponse.ProviderItem] = OrderedDict()
        providers: list[AdminModelConfigResponse.ProviderItem] = []

        for p in base.providers:
            api_key_configured = p.api_key_configured or p.key in updates.api_keys
            updated = AdminModelConfigResponse.ProviderItem(
                key=p.key, provider=p.provider, vendor=p.vendor,
                kinds=p.kinds, base_url=p.base_url, task_base_url=p.task_base_url,
                endpoint_host=p.endpoint_host, task_endpoint_host=p.task_endpoint_host,
                api_key_configured=api_key_configured,
                base_url_configured=p.base_url_configured,
                task_base_url_configured=p.task_base_url_configured,
                extras=p.extras, model_names=p.model_names,
            )
            providers.append(updated)
            providers_by_lookup[_normalize(updated.key)] = updated
            if updated.vendor:
                providers_by_lookup.setdefault(_normalize(updated.vendor), updated)
            if updated.provider:
                providers_by_lookup.setdefault(_normalize(updated.provider), updated)

        models = [
            self._apply_model_api_key_override(
                m,
                providers_by_lookup.get(
                    _first_non_blank(_normalize(m.vendor), _normalize(m.provider))
                ),
            )
            for m in base.models
        ]

        config_errors = list(base.config_errors)
        for err in updates.errors:
            if err not in config_errors:
                config_errors.append(err)

        return AdminModelConfigResponse(
            config_source=base.config_source,
            summary=self._build_summary(models, providers),
            defaults=base.defaults,
            providers=list(providers),
            models=list(models),
            config_errors=list(config_errors),
        )

    @staticmethod
    def _apply_model_api_key_override(
        model: AdminModelConfigResponse.ModelItem,
        provider: AdminModelConfigResponse.ProviderItem | None,
    ) -> AdminModelConfigResponse.ModelItem:
        issues: list[str] = []
        missing = (
            UserModelConfigService.MISSING_API_KEY_ISSUE in model.issues
            if provider is None
            else not provider.api_key_configured
        )
        if missing:
            issues.append(UserModelConfigService.MISSING_API_KEY_ISSUE)
        for issue in model.issues:
            if issue == UserModelConfigService.MISSING_API_KEY_ISSUE or issue in issues:
                continue
            issues.append(issue)
        return AdminModelConfigResponse.ModelItem(
            name=model.name, label=model.label, kind=model.kind,
            provider=model.provider, vendor=model.vendor, family=model.family,
            description=model.description, supports_seed=model.supports_seed,
            supports_responses_api=model.supports_responses_api,
            generation_mode=model.generation_mode,
            supported_sizes=list(model.supported_sizes),
            supported_durations=list(model.supported_durations),
            ready=not issues, config_source=model.config_source,
            endpoint_host=model.endpoint_host,
            task_endpoint_host=model.task_endpoint_host,
            issues=list(issues),
        )

    def _is_api_key_configured(
        self,
        model: AdminModelConfigResponse.ModelItem,
        api_keys: dict[str, str],
        user_id: int,
    ) -> bool:
        if model is None:
            return False
        if self._contains_api_key(api_keys, model.vendor) or self._contains_api_key(api_keys, model.provider):
            return True
        if model.kind == GenerationModelKinds.TEXT:
            return bool(self._model_resolver.resolve_text_profile(model.name, user_id).api_key)
        return bool(self._model_resolver.resolve_media_profile(model.name, model.kind, user_id).api_key)

    @staticmethod
    def _contains_api_key(api_keys: dict[str, str], key: str) -> bool:
        nk = _normalize(key)
        if not nk or not api_keys:
            return False
        return any(_normalize(k) == nk for k in api_keys)

    def _build_summary(
        self,
        models: list[AdminModelConfigResponse.ModelItem],
        providers: list[AdminModelConfigResponse.ProviderItem],
    ) -> AdminModelConfigResponse.Summary:
        provider_count = len(providers) if providers else 0
        vendor_count = len({_normalize(p.vendor) for p in providers if p.vendor}) if providers else 0
        return AdminModelConfigResponse.Summary(
            provider_count=provider_count,
            vendor_count=vendor_count,
            model_count=len(models),
            ready_count=self._count_ready_models(models, None),
            text_ready_count=self._count_ready_models(models, GenerationModelKinds.TEXT),
            image_ready_count=self._count_ready_models(models, GenerationModelKinds.IMAGE),
            video_ready_count=self._count_ready_models(models, GenerationModelKinds.VIDEO),
        )

    @staticmethod
    def _count_ready_models(
        models: list[AdminModelConfigResponse.ModelItem], kind: str | None
    ) -> int:
        return sum(1 for m in models if m.ready and (kind is None or m.kind == kind))

    def _kind_index(self, kind: str) -> int:
        try:
            return self.KIND_ORDER.index(_normalize(kind))
        except ValueError:
            return len(self.KIND_ORDER)

    @staticmethod
    def _provider_group_key(vendor: str, fallback: str) -> str:
        return _first_non_blank(_normalize(vendor), _normalize(fallback))


# =============================================================================
# REPOSITORIES — credential persistence adapters
# =============================================================================
class MybatisUserModelCredentialRepository:
    """Interface for user credential persistence."""

    def find_api_keys_by_user_id(self, user_id: int) -> dict[str, str]:
        raise NotImplementedError

    def save_api_keys(self, user_id: int, api_keys: dict[str, str]) -> None:
        raise NotImplementedError


class SqlAlchemyUserModelCredentialRepository(MybatisUserModelCredentialRepository, RuntimeModelCredentialProvider):
    """Persist and resolve per-user model API keys from sys_user_model_credential."""

    def __init__(self, database_url: str) -> None:
        self._database_url = self._sync_database_url(database_url)
        self._engine = create_engine(self._database_url, future=True)
        self._dialect = make_url(self._database_url).get_backend_name()

    def find_runtime_api_key(self, user_id: int, preferred_scopes: list[str]) -> str:
        keys = self.find_api_keys_by_user_id(user_id)
        for scope in preferred_scopes:
            normalized = _normalize(scope)
            for provider_key, api_key in keys.items():
                if _normalize(provider_key) == normalized:
                    return _first_valid_secret(api_key)
        return ""

    def find_runtime_provider_config(self, user_id: int, preferred_scopes: list[str]) -> RuntimeProviderConfig:
        rows = self.find_provider_configs_by_user_id(user_id)
        for scope in preferred_scopes:
            normalized = _normalize(scope)
            for provider_key, config in rows.items():
                if _normalize(provider_key) == normalized:
                    return config
        return RuntimeProviderConfig()

    def find_api_keys_by_user_id(self, user_id: int) -> dict[str, str]:
        self._ensure_table()
        keys: dict[str, str] = OrderedDict()
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("select provider_key, encrypted_api_key from sys_user_model_credential where user_id = :user_id"),
                {"user_id": user_id},
            ).all()
        for provider_key, api_key in rows:
            key = _normalize(provider_key)
            valid_api_key = _unprotect_user_api_key(api_key)
            if key and valid_api_key:
                keys[key] = valid_api_key
        return keys

    def find_provider_configs_by_user_id(self, user_id: int) -> dict[str, RuntimeProviderConfig]:
        self._ensure_table()
        configs: dict[str, RuntimeProviderConfig] = OrderedDict()
        with self._engine.connect() as conn:
            rows = conn.execute(
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
            key = _normalize(provider_key)
            if not key:
                continue
            configs[key] = RuntimeProviderConfig(
                base_url=_trim_to_empty(base_url),
                task_base_url=_trim_to_empty(task_base_url),
                extras=self._decode_extras_json(extras_json),
            )
        return configs

    def save_api_keys(self, user_id: int, api_keys: dict[str, str]) -> None:
        normalized_updates = {
            _normalize(provider): _first_valid_secret(api_key)
            for provider, api_key in (api_keys or {}).items()
            if _normalize(provider) and _first_valid_secret(api_key)
        }
        if not normalized_updates:
            return
        self._ensure_table()
        now = datetime.now(UTC).isoformat()
        with self._engine.begin() as conn:
            for provider_key, api_key in normalized_updates.items():
                protected_api_key = _protect_user_api_key(api_key)
                if not protected_api_key:
                    continue
                existing = conn.execute(
                    text("select id from sys_user_model_credential where user_id = :user_id and provider_key = :provider_key"),
                    {"user_id": user_id, "provider_key": provider_key},
                ).fetchone()
                if existing:
                    conn.execute(
                        text("update sys_user_model_credential set encrypted_api_key = :api_key, updated_at = :updated_at where id = :id"),
                        {"api_key": protected_api_key, "updated_at": now, "id": existing[0]},
                    )
                else:
                    conn.execute(
                        text(
                            """
                        insert into sys_user_model_credential
                            (user_id, provider_key, encrypted_api_key, base_url, task_base_url, extras_json, created_at, updated_at)
                        values (:user_id, :provider_key, :api_key, :base_url, :task_base_url, :extras_json, :created_at, :updated_at)
                        """,
                        ),
                        {
                            "user_id": user_id,
                            "provider_key": provider_key,
                            "api_key": protected_api_key,
                            "base_url": "",
                            "task_base_url": "",
                            "extras_json": "{}",
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

    def save_provider_configs(self, user_id: int, configs: dict[str, RuntimeProviderConfig]) -> None:
        normalized_updates = {
            _normalize(provider): config
            for provider, config in (configs or {}).items()
            if _normalize(provider)
        }
        if not normalized_updates:
            return
        self._ensure_table()
        now = datetime.now(UTC).isoformat()
        with self._engine.begin() as conn:
            for provider_key, config in normalized_updates.items():
                existing = conn.execute(
                    text("select id from sys_user_model_credential where user_id = :user_id and provider_key = :provider_key"),
                    {"user_id": user_id, "provider_key": provider_key},
                ).fetchone()
                extras_json = json.dumps(config.extras or {}, ensure_ascii=False, sort_keys=True)
                if existing:
                    conn.execute(
                        text(
                            """
                        update sys_user_model_credential
                        set base_url = :base_url, task_base_url = :task_base_url, extras_json = :extras_json, updated_at = :updated_at
                        where id = :id
                        """,
                        ),
                        {
                            "base_url": _trim_to_empty(config.base_url),
                            "task_base_url": _trim_to_empty(config.task_base_url),
                            "extras_json": extras_json,
                            "updated_at": now,
                            "id": existing[0],
                        },
                    )
                else:
                    conn.execute(
                        text(
                            """
                        insert into sys_user_model_credential
                            (user_id, provider_key, encrypted_api_key, base_url, task_base_url, extras_json, created_at, updated_at)
                        values (:user_id, :provider_key, :api_key, :base_url, :task_base_url, :extras_json, :created_at, :updated_at)
                        """,
                        ),
                        {
                            "user_id": user_id,
                            "provider_key": provider_key,
                            "api_key": "",
                            "base_url": _trim_to_empty(config.base_url),
                            "task_base_url": _trim_to_empty(config.task_base_url),
                            "extras_json": extras_json,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

    def _ensure_table(self) -> None:
        if self._dialect != "sqlite":
            return
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                create table if not exists sys_user_model_credential (
                    id integer primary key autoincrement,
                    user_id integer not null,
                    provider_key varchar(64) not null,
                    encrypted_api_key text not null,
                    base_url text not null default '',
                    task_base_url text not null default '',
                    extras_json text not null default '{}',
                    created_at varchar(32) not null,
                    updated_at varchar(32) not null
                )
                """
            )
            columns = {row[1] for row in conn.exec_driver_sql("pragma table_info(sys_user_model_credential)").all()}
            if "base_url" not in columns:
                conn.exec_driver_sql("alter table sys_user_model_credential add column base_url text not null default ''")
            if "task_base_url" not in columns:
                conn.exec_driver_sql("alter table sys_user_model_credential add column task_base_url text not null default ''")
            if "extras_json" not in columns:
                conn.exec_driver_sql("alter table sys_user_model_credential add column extras_json text not null default '{}'")
            conn.exec_driver_sql(
                """
                create unique index if not exists ux_sys_user_model_credential_user_provider
                on sys_user_model_credential(user_id, provider_key)
                """
            )

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
            normalized_key = _trim_to_empty(str(key))
            if not normalized_key:
                continue
            result[normalized_key] = _string_value(value)
        return result

    @staticmethod
    def _sync_database_url(database_url: str) -> str:
        from backend.config import PROJECT_ROOT

        if database_url.startswith("sqlite+aiosqlite:"):
            return database_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
        if database_url.startswith("mysql+asyncmy:"):
            return database_url.replace("mysql+asyncmy:", "mysql+pymysql:", 1)
        if database_url.startswith("sqlite:"):
            return database_url
        if "://" not in database_url:
            return "sqlite:///" + str(PROJECT_ROOT / "data" / "jiandou.db")
        return database_url


class _ProviderCatalogItem:
    """Internal helper for building provider catalog (UserModelConfigService)."""

    def __init__(self, key: str, provider: str, vendor: str):
        self.key = key
        self.provider = provider if provider else key
        self.vendor = vendor if vendor else self.provider
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
            key=self.key, provider=self.provider, vendor=self.vendor,
            kinds=list(self._kinds), base_url="", task_base_url="",
            endpoint_host="", task_endpoint_host="",
            api_key_configured=False, base_url_configured=False,
            task_base_url_configured=False, extras={},
            model_names=list(self._model_names),
        )
