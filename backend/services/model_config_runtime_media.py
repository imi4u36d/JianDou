"""Image and video runtime profile resolution from a loaded configuration snapshot."""

from __future__ import annotations

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_profiles import (
    MediaProviderCapabilities,
    MediaProviderConfig,
    MediaProviderProfile,
    ResolvedModel,
)
from backend.services.model_config_runtime_credentials import (
    RuntimeCredentialResolver,
    provider_property,
    resolve_config_source,
)
from backend.services.model_config_snapshot import ConfigSnapshot, string_value
from backend.services.model_config_values import (
    bool_value,
    configured_provider_model,
    first_non_blank,
    int_value,
    normalize_base_url,
    parse_integer_list,
    parse_string_list,
    resolve_configured_model_section,
    resolve_watermark_default,
    trim_to_empty,
)


def resolve_media_runtime_profile(
    current: ConfigSnapshot,
    credentials: RuntimeCredentialResolver,
    requested_model: str,
    expected_kind: str,
    user_id: int | None = None,
) -> MediaProviderProfile:
    user_scoped = user_id is not None
    model_name = trim_to_empty(requested_model)
    normalized_expected_kind = trim_to_empty(expected_kind).lower()
    if not model_name:
        timeout = int_value(first_non_blank(current.value("model", "timeout_seconds"), "120"), 120)
        return empty_media_runtime_profile(normalized_expected_kind, timeout, current.source)

    canonical_name, section = resolve_configured_model_section(current, model_name)
    resolved = ResolvedModel(canonical_name, section)
    model_section = resolved.section_path()
    model_values = resolved.section
    actual_kind = first_non_blank(string_value(model_values.get("kind")), normalized_expected_kind).lower()
    provider = first_non_blank(string_value(model_values.get("provider")), "")
    provider_section = f"model.providers.{provider}"
    vendor = first_non_blank(string_value(model_values.get("vendor")), current.value(provider_section, "vendor"))
    vendor_section = f"model.providers.{vendor}" if vendor else ""
    user_provider_config = credentials.resolve_user_provider_config(current, user_id, provider, vendor)
    base_url = normalize_base_url(
        first_non_blank(
            user_provider_config.base_url,
            provider_property(provider, "BASE_URL"),
            provider_property(provider, "ENDPOINT"),
            current.value(provider_section, "base_url"),
            current.value(vendor_section, "base_url") if vendor_section else "",
        )
    )
    task_base_url = normalize_base_url(
        first_non_blank(
            user_provider_config.task_base_url,
            provider_property(provider, "TASK_BASE_URL"),
            current.value(f"{provider_section}.extras", "task_base_url"),
            current.value(f"{vendor_section}.extras", "task_base_url") if vendor_section else "",
        )
    )
    api_key = credentials.resolve_api_key(current, user_id, provider, vendor, provider_section)
    source = resolve_config_source(user_scoped, api_key, provider, vendor, current.source, False)
    timeout_seconds = int_value(
        first_non_blank(
            user_provider_config.extras.get("timeout_seconds"),
            provider_property(provider, "TIMEOUT_SECONDS"),
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
            actual_kind,
            model_name,
            provider,
            configured_provider_model(model_name, resolved.canonical_name, resolved.section),
            api_key,
            base_url,
            task_base_url,
            timeout_seconds,
            source,
        ),
        MediaProviderCapabilities(
            supports_seed=bool_value(string_value(model_values.get("supports_seed"))),
            prompt_extend=bool_value(
                first_non_blank(
                    user_provider_config.extras.get("prompt_extend"),
                    current.value(f"{provider_section}.extras", "prompt_extend"),
                    current.value(f"{vendor_section}.extras", "prompt_extend") if vendor_section else "",
                )
            ),
            camera_fixed=bool_value(
                first_non_blank(
                    user_provider_config.extras.get("camera_fixed"),
                    current.value(f"{provider_section}.extras", "camera_fixed"),
                    current.value(f"{vendor_section}.extras", "camera_fixed") if vendor_section else "",
                )
            ),
            watermark=resolve_watermark_default(
                actual_kind,
                first_non_blank(
                    user_provider_config.extras.get("watermark"),
                    current.value(f"{provider_section}.extras", "watermark"),
                    current.value(f"{vendor_section}.extras", "watermark") if vendor_section else "",
                ),
            ),
            poll_interval_seconds=int_value(
                first_non_blank(
                    user_provider_config.extras.get("poll_interval_seconds"),
                    current.value(f"{provider_section}.extras", "poll_interval_seconds"),
                    current.value(f"{vendor_section}.extras", "poll_interval_seconds") if vendor_section else "",
                    "8" if is_video else "5",
                ),
                8 if is_video else 5,
            ),
            poll_timeout_seconds=int_value(
                first_non_blank(
                    user_provider_config.extras.get("poll_timeout_seconds"),
                    current.value(f"{provider_section}.extras", "poll_timeout_seconds"),
                    current.value(f"{vendor_section}.extras", "poll_timeout_seconds") if vendor_section else "",
                    "600" if is_video else "120",
                ),
                600 if is_video else 120,
            ),
            generation_mode=first_non_blank(
                string_value(model_values.get("generation_mode")),
                "i2v" if is_video else "",
            ),
            supported_sizes=parse_string_list(model_values.get("supported_sizes")),
            supported_durations=parse_integer_list(model_values.get("supported_durations")),
            supports_image_data_uri_references=bool_value(
                string_value(model_values.get("supports_image_data_uri_references"))
            ),
        ),
    )


def empty_media_runtime_profile(kind: str, timeout_seconds: int, source: str) -> MediaProviderProfile:
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
