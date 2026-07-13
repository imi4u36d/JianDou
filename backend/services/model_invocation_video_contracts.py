"""Stable contracts shared by video model providers and callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from backend.services.model_config_service import MediaProviderProfile


@dataclass
class VideoGenerationRequest:
    requested_model: str = ""
    prompt: str = ""
    width: int = 720
    height: int = 1280
    duration_seconds: int = 8
    first_frame_url: str = ""
    last_frame_url: str = ""
    seed: int | None = None
    camera_fixed: bool = False
    watermark: bool = False
    return_last_frame: bool = True
    generate_audio: bool = True


@dataclass
class RemoteVideoTaskSubmission:
    provider: str = ""
    requested_model: str = ""
    provider_model: str = ""
    endpoint_host: str = ""
    task_endpoint_host: str = ""
    task_id: str = ""
    first_frame_url: str = ""
    requested_last_frame_url: str = ""
    return_last_frame: bool = False
    generate_audio: bool = False
    prompt: str = ""
    some_int: int = 0
    provider_request: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@dataclass
class RemoteTaskQueryResult:
    task_id: str = ""
    task_status: str = "UNKNOWN"
    video_url: str = ""
    task_message: str = ""
    provider_response: dict[str, Any] = field(default_factory=dict)
    provider_request: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@runtime_checkable
class VideoModelProvider(Protocol):
    def supports(self, profile: MediaProviderProfile) -> bool: ...

    async def submit(
        self, profile: MediaProviderProfile, request: VideoGenerationRequest
    ) -> RemoteVideoTaskSubmission: ...

    async def query(self, profile: MediaProviderProfile, remote_task_id: str) -> RemoteTaskQueryResult: ...
