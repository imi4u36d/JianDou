"""Seedance async video provider implementation."""

from __future__ import annotations

from typing import Any

import httpx

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_config_service import MediaProviderProfile
from backend.services.model_invocation_config import GenerationConfigurationException
from backend.services.model_invocation_video_contracts import (
    RemoteTaskQueryResult,
    RemoteVideoTaskSubmission,
    VideoGenerationRequest,
)
from backend.services.model_invocation_video_transport import VideoProviderTransport


class SeedanceVideoModelProvider:
    def __init__(self, transport: VideoProviderTransport | None = None) -> None:
        self._transport = transport or VideoProviderTransport()

    def supports(self, profile: MediaProviderProfile) -> bool:
        provider = profile.config.provider if profile else ""
        return "seedance" in provider.lower()

    async def submit(
        self,
        profile: MediaProviderProfile,
        request: VideoGenerationRequest,
    ) -> RemoteVideoTaskSubmission:
        if not profile.ready or not profile.task_base_url or not profile.task_base_url.strip():
            raise GenerationConfigurationException("seedance config missing endpoint, task endpoint or api key")
        if not request.first_frame_url or not request.first_frame_url.strip():
            raise GenerationProviderException("seedance video requires firstFrameUrl")
        provider_model = request.requested_model if not profile.config.provider_model else profile.config.provider_model
        body = self._build_request_body(provider_model, request)
        response = await self._transport.send_json(
            profile.base_url,
            profile.api_key,
            body,
            profile.config.timeout_seconds,
            {"X-Api-Key": profile.api_key},
        )
        payload = self._transport.decode(response.text)
        task_id = self._transport.extract_task_id(payload)
        if not task_id:
            raise GenerationProviderException(
                "seedance task response missing task id",
                provider_request={"method": "POST", "endpoint": profile.base_url, "body": body},
                provider_response=payload,
                http_status=response.status_code,
            )
        return RemoteVideoTaskSubmission(
            provider=profile.config.provider,
            requested_model=request.requested_model,
            provider_model=provider_model,
            endpoint_host=profile.endpoint_host,
            task_endpoint_host=profile.task_endpoint_host,
            task_id=task_id,
            first_frame_url=request.first_frame_url,
            requested_last_frame_url=request.last_frame_url or "",
            return_last_frame=request.return_last_frame,
            generate_audio=request.generate_audio,
            prompt=request.prompt,
            provider_request={"method": "POST", "endpoint": profile.base_url, "body": body},
            provider_response=payload,
            http_status=response.status_code,
        )

    async def query(self, profile: MediaProviderProfile, remote_task_id: str) -> RemoteTaskQueryResult:
        task_id = (remote_task_id or "").strip()
        if not task_id:
            raise GenerationProviderException("seedance task id is required")
        if not profile.ready or not profile.task_base_url or not profile.task_base_url.strip():
            raise GenerationConfigurationException("seedance config missing task endpoint or api key")
        poll_url = f"{profile.task_base_url.rstrip('/')}/{self._transport.encode_path_segment(task_id)}"
        request = httpx.Request(
            "GET",
            poll_url,
            headers={
                "Authorization": f"Bearer {profile.api_key}",
                "X-Api-Key": profile.api_key,
                "Accept": "application/json",
            },
        )
        response = await self._transport.send(request, "seedance task query failed")
        payload = self._transport.decode(response.text)
        return RemoteTaskQueryResult(
            task_id=self._transport.extract_task_id(payload) or task_id,
            task_status=self._transport.extract_task_status(payload),
            video_url=self._transport.extract_video_url(payload),
            task_message=self._transport.extract_task_message(payload),
            provider_response=payload,
            provider_request={"method": "GET", "url": poll_url},
            http_status=response.status_code,
        )

    def _build_request_body(
        self,
        provider_model: str,
        request: VideoGenerationRequest,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": request.prompt},
            {
                "type": "image_url",
                "role": "first_frame",
                "image_url": {"url": request.first_frame_url},
            },
        ]
        if request.last_frame_url and request.last_frame_url.strip():
            content.append({
                "type": "image_url",
                "role": "last_frame",
                "image_url": {"url": request.last_frame_url},
            })
        body: dict[str, Any] = {
            "model": provider_model,
            "content": content,
            "ratio": self._aspect_ratio(request.width, request.height),
            "resolution": self._resolution(request.width, request.height),
            "duration": request.duration_seconds,
            "camera_fixed": request.camera_fixed,
            "watermark": request.watermark,
            "return_last_frame": request.return_last_frame,
            "generate_audio": request.generate_audio,
        }
        if request.seed is not None:
            body["seed"] = request.seed
        return body

    @staticmethod
    def _aspect_ratio(width: int, height: int) -> str:
        if width == height:
            return "1:1"
        return "16:9" if width > height else "9:16"

    @staticmethod
    def _resolution(width: int, height: int) -> str:
        longest_edge = max(width, height)
        if longest_edge >= 1920:
            return "1080p"
        if longest_edge >= 1280:
            return "720p"
        return "480p"
