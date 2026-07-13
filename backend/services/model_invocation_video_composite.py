"""Composite routing for video model providers."""

from __future__ import annotations

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_config_service import MediaProviderProfile
from backend.services.model_invocation_video_contracts import (
    RemoteTaskQueryResult,
    RemoteVideoTaskSubmission,
    VideoGenerationRequest,
    VideoModelProvider,
)


class CompositeVideoModelProvider:
    def __init__(self, providers: list[VideoModelProvider] | None = None) -> None:
        self._providers: list[VideoModelProvider] = providers or []

    def supports(self, profile: MediaProviderProfile) -> bool:
        return any(provider.supports(profile) for provider in self._providers)

    async def submit(
        self,
        profile: MediaProviderProfile,
        request: VideoGenerationRequest,
    ) -> RemoteVideoTaskSubmission:
        return await self._resolve(profile).submit(profile, request)

    async def query(self, profile: MediaProviderProfile, remote_task_id: str) -> RemoteTaskQueryResult:
        return await self._resolve(profile).query(profile, remote_task_id)

    def _resolve(self, profile: MediaProviderProfile) -> VideoModelProvider:
        for provider in self._providers:
            if provider.supports(profile):
                return provider
        raise GenerationProviderException(
            f"no video provider supports provider={profile.config.provider}"
        )
