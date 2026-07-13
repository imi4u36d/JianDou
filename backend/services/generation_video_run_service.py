"""Video generation-run creation and asynchronous provider refresh orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from backend.domain.generation_run import GenerationModelKinds, GenerationRunKinds, GenerationRunStatuses
from backend.services.generation_payloads import build_negative_prompt
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.generation_video_run_refresh import GenerationVideoRunRefresher

ProfileResolver = Callable[[str, int | None], dict[str, Any]]
MediaProfileResolver = Callable[[str, str, int | None], dict[str, Any]]
VideoSubmitter = Callable[..., Awaitable[dict[str, Any]]]
VideoQuery = Callable[[dict[str, Any], str], Awaitable[dict[str, Any]]]


class GenerationVideoRunService:
    """Builds video runs and refreshes their asynchronous provider state."""

    _VIDEO_SUCCESS_STATES = {"SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED"}
    _VIDEO_FAILED_STATES = {"FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR"}

    def __init__(
        self,
        support: GenerationRunSupport,
        resolve_text_profile: ProfileResolver,
        resolve_media_profile: MediaProfileResolver,
        call_video_submit: VideoSubmitter,
        call_video_query: VideoQuery,
    ) -> None:
        self._support = support
        self._resolve_text_profile_callback = resolve_text_profile
        self._resolve_media_profile_callback = resolve_media_profile
        self._call_video_submit_callback = call_video_submit
        self._refresher = GenerationVideoRunRefresher(
            support,
            resolve_media_profile,
            call_video_query,
        )

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        return self._resolve_text_profile_callback(requested_model, user_id)

    def _resolve_media_profile(
        self, requested_model: str, media_kind: str, user_id: int | None = None
    ) -> dict[str, Any]:
        return self._resolve_media_profile_callback(requested_model, media_kind, user_id)

    async def _call_video_submit(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self._call_video_submit_callback(*args, **kwargs)

    async def create_video_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        _user_id = self._user_id_from_request(request)
        prompt = self._support.nested_value(request, "input", "prompt", "")
        w, h = self._support.parse_dimensions(
            self._support.nested_value(request, "input", "videoSize", ""),
            self._support.nested_int(request, "input", "width", 720),
            self._support.nested_int(request, "input", "height", 1280),
        )
        _requested_duration = self._support.nested_int(request, "input", "durationSeconds", 8)
        _requested_min_duration = self._support.nested_int(request, "input", "minDurationSeconds", _requested_duration)
        _requested_max_duration = self._support.nested_int(request, "input", "maxDurationSeconds", _requested_duration)
        _requested_seed = self._support.nested_nullable_int(request, "input", "seed")
        _text_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel",
            "",
        )
        requested_video_model = self._support.required_model(
            self._support.nested_value(request, "model", "providerModel", ""),
            "providerModel",
            "",
        )
        video_profile = self._resolve_media_profile(requested_video_model, GenerationModelKinds.VIDEO, _user_id)
        duration = self._normalize_video_duration(
            video_profile, _requested_duration, _requested_min_duration, _requested_max_duration
        )

        _first_frame_url = self.resolve_frame_input(
            self._support.nested_value(request, "input", "firstFrameUrl", ""), "firstFrameUrl"
        )
        _last_frame_url = self.resolve_frame_input(
            self._support.nested_value(request, "input", "lastFrameUrl", ""), "lastFrameUrl"
        )
        _generate_audio = self._support.nested_boolean(request, "input", "generateAudio", True)
        _return_last_frame = self._support.nested_boolean(request, "input", "returnLastFrame", True)
        _text_profile = self._resolve_text_profile(_text_model, _user_id)
        _applied_video_seed = _requested_seed if video_profile.get("supportsSeed", False) else None

        call_chain: list[dict[str, Any]] = []
        provider_interactions: list[dict[str, Any]] = []
        negative_prompt = self._build_negative_prompt("video")
        shaped_prompt = self._support.append_negative_prompt(prompt, negative_prompt)

        _camera_fixed = self._support.infer_camera_fixed(shaped_prompt, video_profile.get("cameraFixed", False))
        _watermark = self._support.nested_boolean(request, "input", "watermark", video_profile.get("watermark", False))

        # Real video submission
        submission = await self._call_video_submit(
            video_profile,
            shaped_prompt,
            w,
            h,
            duration,
            _first_frame_url,
            _last_frame_url,
            _applied_video_seed,
            _camera_fixed,
            _watermark,
            _return_last_frame,
            _generate_audio,
        )
        provider_interactions.append(
            {
                "step": "video.submit",
                "providerRequest": submission["providerRequest"],
                "providerResponse": submission["providerResponse"],
                "httpStatus": submission["httpStatus"],
                "endpointHost": submission["endpointHost"],
                "success": True,
            }
        )

        call_chain.append(
            self._support.call_log(
                "generation",
                "video.submitted",
                "running",
                "",
                {
                    "provider": submission["provider"],
                    "providerModel": submission["providerModel"],
                    "taskId": submission["taskId"],
                    "endpointHost": submission["endpointHost"],
                    "taskEndpointHost": submission["taskEndpointHost"],
                },
            )
        )

        metadata: dict[str, Any] = {
            "outputUrl": "",
            "fileUrl": "",
            "posterUrl": _first_frame_url if _first_frame_url else "",
            "videoSize": self._support.nested_value(request, "input", "videoSize", ""),
            "source": f"remote:{submission['providerModel']}",
            "hasAudio": _generate_audio,
            "textAnalysisProvider": _text_profile.get("provider", ""),
            "textAnalysisModel": _text_profile.get("modelName", ""),
            "configSource": video_profile.get("source", ""),
            "userId": _user_id,
            "remoteSourceUrl": "",
            "provider": submission["provider"],
            "providerModel": submission["providerModel"],
            "requestedModel": requested_video_model,
            "taskId": submission["taskId"],
            "firstFrameUrl": submission["firstFrameUrl"],
            "requestedLastFrameUrl": submission["requestedLastFrameUrl"],
            "providerLastFrameUrl": "",
            "lastFrameUrl": "",
            "last_frame_url": "",
            "returnLastFrame": submission["returnLastFrame"],
            "generateAudio": submission["generateAudio"],
            "requestedDurationSeconds": _requested_duration,
            "appliedDurationSeconds": duration,
            "requestedSeed": _requested_seed,
            "videoGenerationSeed": _applied_video_seed,
            "cameraFixed": _camera_fixed,
            "watermark": _watermark,
            "taskStatus": "SUBMITTED",
            "providerInteractions": provider_interactions,
            "videoSubmitRequest": submission["providerRequest"],
            "videoSubmitResponse": submission["providerResponse"],
            "videoSubmitHttpStatus": submission["httpStatus"],
            "creditFeatureCode": "VIDEO_GENERATION",
            **self._request_metadata(request),
            "videoSubmitInteraction": {
                "step": "video.submit",
                "providerRequest": submission["providerRequest"],
                "providerResponse": submission["providerResponse"],
                "httpStatus": submission["httpStatus"],
                "endpointHost": submission["endpointHost"],
                "success": True,
            },
            "storageRelativeDir": self._support.storage_relative_dir(request, run_id),
            "storageFileStem": self._support.storage_file_stem(request, "video"),
            "nextPollAt": datetime.now(UTC).timestamp() * 1000,
        }

        result: dict[str, Any] = {
            "runId": run_id,
            "kind": GenerationRunKinds.VIDEO,
            "prompt": prompt,
            "shapedPrompt": shaped_prompt,
            "negativePrompt": negative_prompt,
            "outputUrl": "",
            "thumbnailUrl": _first_frame_url if _first_frame_url else "",
            "mimeType": "video/mp4",
            "durationSeconds": duration,
            "width": w,
            "height": h,
            "hasAudio": _generate_audio,
            "metadata": metadata,
            "modelInfo": self._support.build_media_model_info(
                _text_profile,
                None,
                None,
                video_profile,
                requested_video_model,
                GenerationModelKinds.VIDEO,
                None,
                None,
                submission["providerModel"],
                submission["endpointHost"],
                submission["taskEndpointHost"],
                "spring-remote-video-async",
            ),
            "callChain": call_chain,
        }

        return self._support.run_envelope(
            run_id, GenerationRunKinds.VIDEO, request, result, "resultVideo", GenerationRunStatuses.RUNNING
        )

    async def refresh_video_run(self, run: dict[str, Any]) -> dict[str, Any]:
        return await self._refresher.refresh(run)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _user_id_from_request(request: dict[str, Any]) -> int | None:
        auth = request.get("auth", {})
        if isinstance(auth, dict):
            uid = auth.get("userId")
            if isinstance(uid, (int, float)):
                return int(uid)
            if isinstance(uid, str) and uid.strip():
                try:
                    return int(uid.strip())
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _request_metadata(request: dict[str, Any]) -> dict[str, Any]:
        if not request:
            return {}
        return request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}

    @staticmethod
    def _build_negative_prompt(media_kind: str) -> str:
        return build_negative_prompt(media_kind)

    @staticmethod
    def _normalize_video_duration(
        profile: dict[str, Any],
        requested: int,
        min_dur: int,
        max_dur: int,
    ) -> int:
        normalized_requested = max(1, requested)
        normalized_min = max(1, min(min_dur, max_dur))
        normalized_max = max(normalized_min, max(min_dur, max_dur))
        supported = profile.get("supportedDurations", [])
        if not supported:
            return normalized_requested
        in_range = [c for c in supported if normalized_min <= c <= normalized_max]
        candidates = in_range if in_range else supported
        resolved = candidates[0]
        smallest = abs(resolved - normalized_requested)
        for c in candidates:
            d = abs(c - normalized_requested)
            if d < smallest or (d == smallest and c > resolved):
                resolved = c
                smallest = d
        return resolved

    def resolve_frame_input(self, url: str, field_name: str) -> str:
        normalized = url.strip() if url else ""
        if not normalized:
            return ""
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        if normalized.startswith("data:image/") and ";base64," in normalized:
            return normalized
        if normalized.startswith("/storage/"):
            data_uri = self._support.image_data_uri_from_public_url(normalized)
            if data_uri:
                return data_uri
            external_url = self._support.build_externally_accessible_url(normalized)
            if external_url.startswith("http://") or external_url.startswith("https://"):
                return external_url
        return ""
