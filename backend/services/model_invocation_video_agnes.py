"""Agnes async video provider implementation."""

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


class AgnesVideoModelProvider:
    def __init__(self, transport: VideoProviderTransport | None = None) -> None:
        self._transport = transport or VideoProviderTransport()

    def supports(self, profile: MediaProviderProfile) -> bool:
        provider = profile.config.provider if profile else ""
        return "agnes" in provider.lower()

    async def submit(
        self,
        profile: MediaProviderProfile,
        request: VideoGenerationRequest,
    ) -> RemoteVideoTaskSubmission:
        if not profile.ready:
            raise GenerationConfigurationException("agnes config missing endpoint or api key")
        provider_model = request.requested_model if not profile.config.provider_model else profile.config.provider_model
        body = self._build_request_body(provider_model, request, frame_rate=24)
        response = await self._transport.send_json(
            profile.base_url,
            profile.api_key,
            body,
            profile.config.timeout_seconds,
            {"Authorization": f"Bearer {profile.api_key}"},
        )
        payload = self._transport.decode(response.text)
        task_id = self._transport.extract_task_id(payload)
        if not task_id:
            raise GenerationProviderException(
                "agnes task response missing task id",
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
            raise GenerationProviderException("agnes task id is required")
        if not profile.ready:
            raise GenerationConfigurationException("agnes config missing task endpoint or api key")
        poll_url = f"{(profile.task_base_url or profile.base_url).rstrip('/')}/{task_id}"
        request = httpx.Request(
            "GET",
            poll_url,
            headers={"Authorization": f"Bearer {profile.api_key}", "Accept": "application/json"},
        )
        response = await self._transport.send(request, "agnes task query failed")
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
        frame_rate: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": provider_model,
            "prompt": request.prompt,
            "width": request.width,
            "height": request.height,
            "num_frames": self._compute_num_frames(request.duration_seconds, frame_rate),
            "frame_rate": frame_rate,
        }
        first = request.first_frame_url.strip() if request.first_frame_url else ""
        last = request.last_frame_url.strip() if request.last_frame_url else ""
        if first and last:
            body.update(
                mode="keyframes",
                image=first,
                extra_body={"image": [first, last], "mode": "keyframes"},
            )
        elif first:
            body["image"] = first
        if request.seed is not None:
            body["seed"] = request.seed
        return body

    @staticmethod
    def _compute_num_frames(duration_seconds: int, frame_rate: int = 24) -> int:
        target = duration_seconds * frame_rate
        best = 81
        for multiplier in range(10, 56):
            candidate = 8 * multiplier + 1
            if abs(candidate - target) < abs(best - target):
                best = candidate
        return min(best, 441)
