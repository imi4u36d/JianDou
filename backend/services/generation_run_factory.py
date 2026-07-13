"""Generation run construction, provider coordination, and graceful fallbacks."""

from __future__ import annotations

import logging
from typing import Any

from backend.services.generation_image_run_service import GenerationImageRunService
from backend.services.generation_profile_presenters import (
    media_profile_dict,
    stub_media_profile,
    stub_text_profile,
    text_profile_dict,
)
from backend.services.generation_provider_registry import (
    default_image_providers,
    default_model_config_resolver,
    default_prompt_resolver,
    default_text_provider,
    default_video_provider,
)
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_text_run_service import GenerationTextRunService
from backend.services.generation_video_run_service import GenerationVideoRunService
from backend.services.model_config_service import ModelRuntimePropertiesResolver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Real model provider singletons (lazy-initialized to avoid circular imports)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


# =============================================================================
# EXCEPTIONS
# =============================================================================
class GenerationProviderException(Exception):
    """Raised when a provider (text/image/video API) returns an error."""

    def __init__(
        self,
        message: str,
        provider_request: dict[str, Any] | None = None,
        provider_response: Any = None,
        http_status: int = 0,
    ) -> None:
        super().__init__(message)
        self.provider_request = provider_request or {}
        self.provider_response = provider_response
        self.http_status = http_status


class GenerationNotImplementedException(Exception):
    """Raised when a generation feature is not yet implemented."""

    pass


class GenerationRunNotFoundException(Exception):
    """Raised when a run ID is not found."""

    pass


class UnsupportedGenerationKindException(Exception):
    """Raised when an unsupported kind is requested."""

    def __init__(self, kind: str) -> None:
        super().__init__(f"不支持的生成类型: {kind}")


# ===========================================================================
# GenerationRunFactory
# ===========================================================================


# =============================================================================
# GENERATION RUN FACTORY
# =============================================================================
class GenerationRunFactory:
    """Creates generation runs by dispatching to remote model providers.

    Mirrors the Java GenerationRunFactory.
    External provider calls return stub data since those integrations are
    not the focus of this port.
    """

    def __init__(
        self,
        support: GenerationRunSupport | None = None,
        config_resolver: ModelRuntimePropertiesResolver | None = None,
        text_provider: Any | None = None,
        prompt_resolver: Any | None = None,
        image_providers: list | None = None,
        video_provider: Any | None = None,
    ) -> None:
        self._support = support or GenerationRunSupport()
        self._config_resolver = config_resolver or default_model_config_resolver
        self._text_provider = text_provider or default_text_provider()
        self._prompt_resolver = prompt_resolver or default_prompt_resolver()
        self._image_providers = image_providers or default_image_providers()
        self._video_provider = video_provider or default_video_provider()

    # ------------------------------------------------------------------
    # Public creation methods
    # ------------------------------------------------------------------

    def _text_run_service(self) -> GenerationTextRunService:
        return GenerationTextRunService(
            support=self._support,
            prompt_resolver=self._prompt_resolver,
            resolve_text_profile=self._resolve_text_profile,
            call_text_model=self._call_text_model,
        )

    def _image_run_service(self) -> GenerationImageRunService:
        return GenerationImageRunService(
            support=self._support,
            resolve_text_profile=self._resolve_text_profile,
            resolve_media_profile=self._resolve_media_profile,
            call_image_model=self._call_image_model,
        )

    async def create_probe_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._text_run_service().create_probe_run(run_id, request)

    async def create_script_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._text_run_service().create_script_run(run_id, request)

    async def create_script_adjust_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._text_run_service().create_script_adjust_run(run_id, request)

    async def create_image_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._image_run_service().create_image_run(run_id, request)

    def _video_run_service(self) -> GenerationVideoRunService:
        return GenerationVideoRunService(
            support=self._support,
            resolve_text_profile=self._resolve_text_profile,
            resolve_media_profile=self._resolve_media_profile,
            call_video_submit=self._call_video_submit,
            call_video_query=self._call_video_query,
        )

    async def create_video_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self._video_run_service().create_video_run(run_id, request)

    async def refresh_video_run(self, run: dict[str, Any]) -> dict[str, Any]:
        return await self._video_run_service().refresh_video_run(run)

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        """Resolve text model profile using the real config resolver."""
        try:
            profile = self._config_resolver.resolve_text_profile(requested_model, user_id)
            return text_profile_dict(profile, requested_model, user_id)
        except Exception as ex:
            logger.warning("Failed to resolve text profile for %s: %s", requested_model, ex)
            return self._stub_resolve_text_profile(requested_model)

    async def _call_text_model(
        self,
        profile_dict: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Call the real text model provider and return a response dict compatible with existing code."""
        from backend.services.model_invocation import TextModelInvocation

        profile = self._config_resolver.resolve_text_profile(
            profile_dict.get("requestedModel", "") or profile_dict.get("modelName", ""),
            profile_dict.get("userId"),
        )
        invocation = TextModelInvocation(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=profile_dict.get("temperature", 0.15),
            max_tokens=profile_dict.get("maxTokens", 4096),
        )
        result = await self._text_provider.generate(profile, invocation)
        return {
            "text": result.text,
            "modelName": profile_dict.get("modelName", ""),
            "latencyMs": result.latency_ms,
            "endpointHost": result.endpoint_host,
            "providerRequest": result.provider_request,
            "providerResponse": result.provider_response,
            "httpStatus": result.http_status,
            "responseId": result.response_id,
            "responsesApi": result.responses_api,
        }

    def _resolve_media_profile(
        self,
        requested_model: str,
        media_kind: str,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Resolve media model profile using the real config resolver."""
        try:
            profile = self._config_resolver.resolve_media_profile(requested_model, media_kind, user_id)
            return media_profile_dict(profile, requested_model, user_id)
        except Exception as ex:
            logger.warning("Failed to resolve media profile for %s (%s): %s", requested_model, media_kind, ex)
            return self._stub_resolve_media_profile(requested_model, media_kind)

    async def _call_image_model(
        self,
        profile_dict: dict[str, Any],
        prompt: str,
        width: int,
        height: int,
        reference_image_urls: list[str],
        seed: int | None,
    ) -> dict[str, Any]:
        """Call the real image model provider via the first matching provider."""
        from backend.services.model_invocation import (
            GenerationConfigurationException,
            ImageGenerationRequest,
        )

        profile = self._config_resolver.resolve_image_profile(
            profile_dict.get("requestedModel", "") or profile_dict.get("modelName", ""),
            profile_dict.get("userId"),
        )
        request = ImageGenerationRequest(
            requested_model=profile_dict.get("modelName", ""),
            prompt=prompt,
            width=width,
            height=height,
            reference_image_urls=reference_image_urls,
            seed=seed,
        )

        # Find the provider that supports this profile
        for provider in self._image_providers:
            if provider.supports(profile):
                result = await provider.generate(profile, request)
                return {
                    "provider": result.provider,
                    "providerModel": result.provider_model,
                    "mimeType": result.mime_type,
                    "data": result.data,
                    "remoteSourceUrl": result.remote_source_url,
                    "endpointHost": result.endpoint_host,
                    "providerRequest": result.provider_request,
                    "providerResponse": result.provider_response,
                    "httpStatus": result.http_status,
                    "requestedSize": result.requested_size,
                }

        raise GenerationConfigurationException(f"no image provider found for provider={profile.config.provider}")

    async def _call_video_submit(
        self,
        profile_dict: dict[str, Any],
        prompt: str,
        width: int,
        height: int,
        duration_seconds: int,
        first_frame_url: str,
        last_frame_url: str,
        seed: int | None,
        camera_fixed: bool,
        watermark: bool,
        return_last_frame: bool,
        generate_audio: bool,
    ) -> dict[str, Any]:
        """Call the real video model provider to submit a task."""
        from backend.services.model_invocation import VideoGenerationRequest

        profile = self._config_resolver.resolve_video_profile(
            profile_dict.get("requestedModel", "") or profile_dict.get("modelName", ""),
            profile_dict.get("userId"),
        )
        request = VideoGenerationRequest(
            requested_model=profile_dict.get("modelName", ""),
            prompt=prompt,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            first_frame_url=first_frame_url,
            last_frame_url=last_frame_url,
            seed=seed,
            camera_fixed=camera_fixed,
            watermark=watermark,
            return_last_frame=return_last_frame,
            generate_audio=generate_audio,
        )
        result = await self._video_provider.submit(profile, request)
        return {
            "provider": result.provider,
            "providerModel": result.provider_model,
            "taskId": result.task_id,
            "endpointHost": result.endpoint_host,
            "taskEndpointHost": result.task_endpoint_host,
            "providerRequest": result.provider_request,
            "providerResponse": result.provider_response,
            "httpStatus": result.http_status,
            "firstFrameUrl": result.first_frame_url,
            "requestedLastFrameUrl": result.requested_last_frame_url,
            "returnLastFrame": result.return_last_frame,
            "generateAudio": result.generate_audio,
        }

    async def _call_video_query(
        self,
        profile_dict: dict[str, Any],
        task_id: str,
    ) -> dict[str, Any]:
        """Query video task status from the real provider."""
        profile = self._config_resolver.resolve_video_profile(
            profile_dict.get("requestedModel", "") or profile_dict.get("modelName", ""),
            user_id=profile_dict.get("userId"),
        )
        result = await self._video_provider.query(profile, task_id)
        return {
            "taskId": result.task_id,
            "taskStatus": result.task_status,
            "videoUrl": result.video_url,
            "taskMessage": result.task_message,
            "providerResponse": result.provider_response,
            "providerRequest": result.provider_request,
            "httpStatus": result.http_status,
        }

    @staticmethod
    def _stub_resolve_text_profile(requested_model: str) -> dict[str, Any]:
        return stub_text_profile(requested_model)

    @staticmethod
    def _stub_resolve_media_profile(requested_model: str, media_kind: str) -> dict[str, Any]:
        return stub_media_profile(requested_model, media_kind)

    def _resolve_video_frame_input(self, url: str, field_name: str) -> str:
        """Compatibility hook delegated to the video run service."""
        return self._video_run_service().resolve_frame_input(url, field_name)
