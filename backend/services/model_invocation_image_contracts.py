"""Stable contracts shared by image model providers and callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from backend.services.model_config_profiles import MediaProviderProfile


@dataclass
class ImageGenerationRequest:
    requested_model: str = ""
    prompt: str = ""
    width: int = 1024
    height: int = 1024
    reference_image_urls: list[str] = field(default_factory=list)
    reference_image_url: str = ""
    seed: int | None = None


@dataclass
class RemoteImageGenerationResult:
    data: bytes = b""
    mime_type: str = "image/png"
    remote_source_url: str = ""
    provider: str = ""
    provider_model: str = ""
    endpoint_host: str = ""
    width: int = 0
    height: int = 0
    requested_size: str = ""
    some_int: int = 0
    provider_request: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@runtime_checkable
class ImageModelProvider(Protocol):
    def supports(self, profile: MediaProviderProfile) -> bool: ...

    def generate(
        self, profile: MediaProviderProfile, request: ImageGenerationRequest
    ) -> RemoteImageGenerationResult: ...


@dataclass
class DownloadedBinary:
    data: bytes = b""
    mime_type: str = ""


@dataclass
class MultipartFilePart:
    field_name: str = ""
    file_name: str = ""
    content_type: str = "application/octet-stream"
    data: bytes = b""
