"""Text model runtime profile resolution from a loaded configuration snapshot."""

from __future__ import annotations

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_profiles import (
    ModelRuntimeProfile,
    ResolvedModel,
    TextProviderCapabilities,
    TextProviderConfig,
)
from backend.services.model_config_runtime_credentials import (
    RuntimeCredentialResolver,
    env_value,
    provider_property,
    resolve_config_source,
)
from backend.services.model_config_snapshot import ConfigSnapshot, string_value
from backend.services.model_config_values import (
    bool_value,
    configured_provider_model,
    derive_base_url_from_host,
    double_value,
    first_non_blank,
    int_value,
    normalize_base_url,
    resolve_configured_model_section,
    resolve_text_supports_responses_api,
    trim_to_empty,
)


def resolve_text_runtime_profile(
    current: ConfigSnapshot,
    credentials: RuntimeCredentialResolver,
    requested_model: str,
    user_id: int | None = None,
) -> ModelRuntimeProfile:
    user_scoped = user_id is not None
    model_name = trim_to_empty(requested_model)
    if not model_name:
        return _empty_text_profile(current)

    canonical_name, section = resolve_configured_model_section(current, model_name)
    resolved = ResolvedModel(canonical_name, section)
    model_section = resolved.section_path()
    model_values = resolved.section
    kind = first_non_blank(string_value(model_values.get("kind")), GenerationModelKinds.TEXT).lower()
    provider = first_non_blank(
        env_value("JIANDOU_MODEL_PROVIDER"),
        string_value(model_values.get("provider")),
        "",
    )
    provider_section = f"model.providers.{provider}"
    vendor = first_non_blank(string_value(model_values.get("vendor")), current.value(provider_section, "vendor"))
    user_provider_config = credentials.resolve_user_provider_config(current, user_id, provider, vendor)
    api_key = credentials.resolve_api_key(current, user_id, provider, vendor, provider_section)
    base_url = normalize_base_url(
        first_non_blank(
            user_provider_config.base_url,
            env_value("JIANDOU_MODEL_BASE_URL"),
            env_value("JIANDOU_MODEL_ENDPOINT"),
            provider_property(provider, "BASE_URL"),
            provider_property(provider, "ENDPOINT"),
            current.value(provider_section, "base_url"),
            derive_base_url_from_host(env_value("JIANDOU_MODEL_ENDPOINT_HOST")),
            "",
        )
    )
    timeout_seconds = int_value(
        first_non_blank(
            user_provider_config.extras.get("timeout_seconds"),
            env_value("JIANDOU_MODEL_TIMEOUT"),
            current.value(model_section, "timeout_seconds"),
            current.value(f"{provider_section}.extras", "timeout_seconds"),
            current.value("model", "timeout_seconds"),
            "120",
        ),
        120,
    )
    temperature = double_value(
        first_non_blank(
            env_value("JIANDOU_MODEL_TEMPERATURE"),
            current.value(model_section, "temperature"),
            current.value("model", "temperature"),
            "0.15",
        ),
        0.15,
    )
    max_tokens = int_value(
        first_non_blank(
            env_value("JIANDOU_MODEL_MAX_TOKENS"),
            current.value(model_section, "max_tokens"),
            current.value("model", "max_tokens"),
            "2000",
        ),
        2000,
    )
    source = resolve_config_source(
        user_scoped,
        api_key,
        provider,
        vendor,
        current.source,
        bool(env_value("JIANDOU_MODEL_PROVIDER")),
    )
    configured_responses_api = first_non_blank(user_provider_config.extras.get("use_responses_api"))
    supports_responses_api = (
        bool_value(configured_responses_api)
        if configured_responses_api
        else resolve_text_supports_responses_api(current, provider_section, provider, base_url)
    )
    return ModelRuntimeProfile(
        TextProviderConfig(
            kind,
            model_name,
            provider,
            configured_provider_model(model_name, resolved.canonical_name, resolved.section),
            api_key,
            base_url,
            timeout_seconds,
            temperature,
            max_tokens,
            source,
        ),
        TextProviderCapabilities(
            bool_value(string_value(model_values.get("supports_seed"))),
            supports_responses_api,
        ),
    )


def _empty_text_profile(current: ConfigSnapshot) -> ModelRuntimeProfile:
    return ModelRuntimeProfile(
        TextProviderConfig(
            kind="",
            model="",
            provider="",
            provider_model="",
            api_key="",
            base_url="",
            timeout_seconds=int_value(first_non_blank(current.value("model", "timeout_seconds"), "120"), 120),
            temperature=double_value(first_non_blank(current.value("model", "temperature"), "0.15"), 0.15),
            max_tokens=int_value(first_non_blank(current.value("model", "max_tokens"), "2000"), 2000),
            source=current.source,
        ),
        TextProviderCapabilities(False, False),
    )
