"""Stable request and response contracts for model configuration services."""

from __future__ import annotations

from dataclasses import dataclass, field


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
    summary: Summary
    defaults: Defaults
    providers: list[ProviderItem]
    models: list[ModelItem]
    config_errors: list[str]


@dataclass
class AdminModelConfigValidationResponse:
    valid: bool
    snapshot: AdminModelConfigResponse


@dataclass
class ApiKeyUpdateBatch:
    api_keys: dict[str, str]
    errors: list[str]
