"""Pure value helpers for model runtime configuration."""

from __future__ import annotations

from urllib.parse import urlparse

from backend.domain.generation_run import GenerationModelKinds
from backend.services.model_config_snapshot import ConfigSnapshot, normalize_map, string_value


def trim_to_empty(value: str | None) -> str:
    return "" if value is None else value.strip()


def normalize(value: str | None) -> str:
    return trim_to_empty(value).lower()


def first_non_blank(*values: str | None) -> str:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return ""


def first_valid_secret(*values: str | None) -> str:
    for value in values:
        candidate = trim_to_empty(value)
        if candidate and candidate not in {"1", "changeme", "placeholder"}:
            return candidate
    return ""


def int_value(raw: str, fallback: int) -> int:
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return fallback


def double_value(raw: str, fallback: float) -> float:
    try:
        return float(raw.strip())
    except (ValueError, AttributeError):
        return fallback


def bool_value(raw: str) -> bool:
    return normalize(raw) in ("1", "true", "yes", "on")


def parse_string_list(raw: object) -> list[str]:
    text = string_value(raw)
    if not text:
        return []
    seen: list[str] = []
    for item in text.split(","):
        trimmed = item.strip()
        if trimmed and trimmed not in seen:
            seen.append(trimmed)
    return seen


def parse_integer_list(raw: object) -> list[int]:
    text = string_value(raw)
    if not text:
        return []
    result: list[int] = []
    for item in text.split(","):
        parsed = int_value(item, -1)
        if parsed > 0 and parsed not in result:
            result.append(parsed)
    return result


def host_of(raw: str) -> str:
    try:
        parsed = urlparse(raw)
        return parsed.hostname or ""
    except Exception:
        return ""


def derive_base_url_from_host(host: str) -> str:
    value = trim_to_empty(host)
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return trim_to_empty(value.rstrip("/"))
    return f"https://{value}/v1"


def normalize_base_url(raw: str) -> str:
    value = trim_to_empty(raw)
    if not value:
        return ""
    normalized = value.rstrip("/")
    if normalized.endswith("/responses"):
        return normalized[: -len("/responses")]
    if normalized.endswith("/chat/completions"):
        return normalized[: -len("/chat/completions")]
    return normalized


def resolve_text_supports_responses_api(
    current: ConfigSnapshot,
    provider_section: str,
    provider: str,
    base_url: str,
) -> bool:
    configured = current.value(f"{provider_section}.extras", "use_responses_api")
    if configured:
        return bool_value(configured)
    normalized_provider = normalize(provider)
    normalized_base_url = normalize(base_url)
    return (
        normalized_provider in ("openai",)
        or "ark" in normalized_provider
        or "volc" in normalized_provider
        or "openai.com" in normalized_base_url
        or "volces.com/api/v3" in normalized_base_url
    )


def resolve_configured_model_section(
    current: ConfigSnapshot,
    requested_model: str,
) -> tuple[str, dict[str, object]]:
    model_name = trim_to_empty(requested_model)
    if not model_name:
        return "", {}
    direct = current.map("model.models").get(model_name)
    if isinstance(direct, dict):
        return model_name, normalize_map(direct)
    return model_name, {}


def configured_provider_model(
    requested_model: str,
    canonical_name: str,
    section: dict[str, object],
) -> str:
    return first_non_blank(
        string_value(section.get("provider_model")),
        canonical_name,
        trim_to_empty(requested_model),
    )


def resolve_watermark_default(kind: str, configured_watermark: str) -> bool:
    if configured_watermark:
        return bool_value(configured_watermark)
    return kind != GenerationModelKinds.IMAGE
