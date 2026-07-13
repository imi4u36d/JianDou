"""Stable runtime model configuration value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.model_config_values import host_of


@dataclass
class ResolvedModel:
    canonical_name: str
    section: dict[str, Any]

    def section_path(self) -> str:
        if not self.canonical_name:
            return ""
        return f'model.models."{self.canonical_name}"'


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
        return host_of(self.config.base_url)

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
        return host_of(self.config.base_url)

    @property
    def task_endpoint_host(self) -> str:
        return host_of(self.config.task_base_url)

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
