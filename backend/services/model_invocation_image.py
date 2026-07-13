"""Image-model contracts, HTTP transport, and OpenAI-compatible provider."""

from __future__ import annotations

import base64
from typing import Any

from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL
from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_config_profiles import MediaProviderProfile
from backend.services.model_invocation_config import GenerationConfigurationException
from backend.services.model_invocation_image_contracts import (
    DownloadedBinary,
    ImageGenerationRequest,
    ImageModelProvider,
    MultipartFilePart,
    RemoteImageGenerationResult,
)
from backend.services.model_invocation_image_transport import ImageProviderTransport

__all__ = [
    "DownloadedBinary",
    "ImageGenerationRequest",
    "ImageModelProvider",
    "ImageProviderTransport",
    "MultipartFilePart",
    "OpenAiImageModelProvider",
    "RemoteImageGenerationResult",
]


# =============================================================================
# OpenAiImageModelProvider
# =============================================================================


class OpenAiImageModelProvider:
    """OpenAI GPT Image API provider."""

    def __init__(self, transport: ImageProviderTransport | None = None):
        self._transport = transport or ImageProviderTransport()

    def supports(self, profile: MediaProviderProfile) -> bool:
        provider = profile.config.provider if profile else ""
        return provider.strip().lower() == "openai" and getattr(profile.config, "kind", "") == "image"

    async def generate(
        self,
        profile: MediaProviderProfile,
        request: ImageGenerationRequest,
    ) -> RemoteImageGenerationResult:
        if not profile.ready:
            raise GenerationConfigurationException("image provider config missing api key or base url")
        reference_image_urls = self._normalize_reference_image_urls(
            request.reference_image_urls, request.reference_image_url
        )
        if reference_image_urls:
            return await self._generate_image_to_image(profile, request, reference_image_urls)
        return await self._generate_text_to_image(profile, request)

    # ------------------------------------------------------------------
    # Text-to-image
    # ------------------------------------------------------------------

    async def _generate_text_to_image(
        self,
        profile: MediaProviderProfile,
        request: ImageGenerationRequest,
    ) -> RemoteImageGenerationResult:
        provider_model = self._required_provider_model(profile, request)
        size = self._requested_image_size(request)
        request_body: dict[str, Any] = {
            "model": provider_model,
            "prompt": request.prompt,
            "size": size,
            "output_format": "png",
        }

        response = await self._transport.send_json(
            self._image_endpoint(profile.base_url, "generations"),
            profile.api_key,
            request_body,
            profile.config.timeout_seconds,
        )
        payload = self._transport.decode(response.text)
        provider_request: dict[str, Any] = {
            "method": "POST",
            "endpoint": self._image_endpoint(profile.base_url, "generations"),
            "body": request_body,
        }
        return await self._parse_openai_image_response(
            payload, provider_request, response.status_code,
            profile, provider_model, request,
        )

    # ------------------------------------------------------------------
    # Image-to-image
    # ------------------------------------------------------------------

    async def _generate_image_to_image(
        self,
        profile: MediaProviderProfile,
        request: ImageGenerationRequest,
        reference_image_urls: list[str],
    ) -> RemoteImageGenerationResult:
        provider_model = self._required_provider_model(profile, request)
        size = self._requested_image_size(request)
        files = await self._reference_urls_to_file_parts(reference_image_urls, profile.config.timeout_seconds)
        if not files:
            raise GenerationProviderException("openai image edits require at least one usable reference image")
        fields = {
            "model": provider_model,
            "prompt": request.prompt,
            "size": size,
            "output_format": "png",
        }
        endpoint = self._image_endpoint(profile.base_url, "edits")
        request_payload = {
            "method": "POST",
            "endpoint": endpoint,
            "fields": fields,
            "files": [{"fieldName": f.field_name, "fileName": f.file_name, "contentType": f.content_type} for f in files],
        }
        response = await self._transport.send_multipart(
            endpoint,
            profile.api_key,
            fields,
            files,
            profile.config.timeout_seconds,
            request_payload=request_payload,
        )

        payload = self._transport.decode(response.text)
        return await self._parse_openai_image_response(
            payload, request_payload, response.status_code,
            profile, provider_model, request,
        )

    # ------------------------------------------------------------------
    # Response parsing (OpenAI-compatible images/generations)
    # ------------------------------------------------------------------

    async def _parse_openai_image_response(
        self,
        payload: dict[str, Any],
        provider_request: dict[str, Any],
        http_status: int,
        profile: MediaProviderProfile,
        provider_model: str,
        request: ImageGenerationRequest,
    ) -> RemoteImageGenerationResult:
        data_list = payload.get("data")
        if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
            raise GenerationProviderException(
                "openai image response did not include data array",
                provider_request=provider_request,
                provider_response=payload,
                http_status=http_status,
            )
        first_item = data_list[0]
        source_url = self._transport.extract_first_string(first_item, "url")

        data: bytes
        mime_type = "image/png"
        if source_url:
            binary = await self._transport.download_binary(source_url, profile.config.timeout_seconds)
            data = binary.data
            mime_type = binary.mime_type if binary.mime_type else mime_type
        else:
            b64 = self._transport.extract_first_string(first_item, "b64_json")
            if not b64:
                raise GenerationProviderException(
                    "openai image response did not include usable image data (no url or b64_json)",
                    provider_request=provider_request,
                    provider_response=payload,
                    http_status=http_status,
                )
            try:
                data = base64.b64decode(b64)
            except (ValueError, base64.binascii.Error):
                raise GenerationProviderException(
                    "openai image response returned invalid base64 image data",
                    provider_request=provider_request,
                    provider_response=payload,
                    http_status=http_status,
                )

        return RemoteImageGenerationResult(
            data=data,
            mime_type=mime_type,
            remote_source_url=source_url,
            provider=profile.config.provider,
            provider_model=provider_model,
            endpoint_host=profile.endpoint_host,
            width=request.width,
            height=request.height,
            requested_size=self._requested_image_size(request),
            provider_request=provider_request,
            provider_response=payload,
            http_status=http_status,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _requested_image_size(request: ImageGenerationRequest) -> str:
        if request.width <= 0 or request.height <= 0:
            return "auto"
        return f"{request.width}x{request.height}"

    async def _reference_urls_to_file_parts(
        self,
        urls: list[str],
        timeout_seconds: int,
    ) -> list[MultipartFilePart]:
        files: list[MultipartFilePart] = []
        for idx, url in enumerate(urls, start=1):
            normalized = (url or "").strip()
            if not normalized:
                continue
            if normalized.startswith("data:image/") and ";base64," in normalized:
                header, b64 = normalized.split(";base64,", 1)
                mime = header[len("data:"):] or "image/png"
                try:
                    data = base64.b64decode(b64)
                except (ValueError, base64.binascii.Error):
                    continue
            else:
                binary = await self._transport.download_binary(normalized, timeout_seconds)
                data = binary.data
                mime = binary.mime_type or "image/png"
            files.append(MultipartFilePart(
                field_name="image[]",
                file_name=f"reference-{idx}.{self._extension_for_mime(mime)}",
                content_type=mime,
                data=data,
            ))
        return files

    @staticmethod
    def _normalize_reference_image_urls(
        reference_image_urls: list[str],
        reference_image_url: str,
    ) -> list[str]:
        normalized: list[str] = []
        if reference_image_urls:
            for value in reference_image_urls:
                if value and value.strip():
                    normalized.append(value.strip())
        if not normalized and reference_image_url and reference_image_url.strip():
            normalized.append(reference_image_url.strip())
        return normalized

    @staticmethod
    def _image_endpoint(base_url: str, kind: str) -> str:
        normalized = (base_url or "").rstrip("/")
        for suffix in ("/images/generations", "/images/edits"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return f"{normalized}/images/{kind}"

    @staticmethod
    def _extension_for_mime(mime_type: str) -> str:
        normalized = (mime_type or "").split(";", 1)[0].strip().lower()
        if normalized == "image/jpeg":
            return "jpg"
        if normalized == "image/webp":
            return "webp"
        return "png"

    @staticmethod
    def _required_provider_model(
        profile: MediaProviderProfile,
        request: ImageGenerationRequest,
    ) -> str:
        provider_model = OpenAiImageModelProvider._blank_to(
            profile.config.provider_model if profile and profile.config else "",
            request.requested_model,
        )
        if provider_model:
            return provider_model
        return DEFAULT_OPENAI_IMAGE_MODEL

    @staticmethod
    def _blank_to(primary: str, fallback: str) -> str:
        return fallback if not primary else primary
