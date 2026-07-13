"""Image generation-run orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.domain.generation_run import DEFAULT_OPENAI_IMAGE_MODEL, GenerationModelKinds, GenerationRunKinds
from backend.services.generation_payloads import build_negative_prompt
from backend.services.generation_run_support import GenerationRunSupport

ProfileResolver = Callable[[str, int | None], dict[str, Any]]
MediaProfileResolver = Callable[[str, str, int | None], dict[str, Any]]
ImageModelCall = Callable[..., Awaitable[dict[str, Any]]]


class GenerationImageRunService:
    """Builds image runs and materializes generated artifacts."""

    def __init__(
        self,
        support: GenerationRunSupport,
        resolve_text_profile: ProfileResolver,
        resolve_media_profile: MediaProfileResolver,
        call_image_model: ImageModelCall,
    ) -> None:
        self._support = support
        self._resolve_text_profile_callback = resolve_text_profile
        self._resolve_media_profile_callback = resolve_media_profile
        self._call_image_model_callback = call_image_model

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        return self._resolve_text_profile_callback(requested_model, user_id)

    def _resolve_media_profile(
        self, requested_model: str, media_kind: str, user_id: int | None = None
    ) -> dict[str, Any]:
        return self._resolve_media_profile_callback(requested_model, media_kind, user_id)

    async def _call_image_model(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self._call_image_model_callback(*args, **kwargs)

    async def create_image_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        _user_id = self._user_id_from_request(request)
        prompt = self._support.nested_value(request, "input", "prompt", "")
        reference_image_url = self._support.nested_value(request, "input", "referenceImageUrl", "")
        reference_image_urls: list[str] = list(self._support.nested_string_list(request, "input", "referenceImageUrls"))
        if not reference_image_urls and reference_image_url:
            reference_image_urls.append(reference_image_url)
        if not reference_image_url and reference_image_urls:
            reference_image_url = reference_image_urls[0]
        frame_role = self._support.normalize_frame_role(
            self._support.nested_value(request, "input", "frameRole", "first")
        )
        width = self._support.nested_int(request, "input", "width", 1024)
        height = self._support.nested_int(request, "input", "height", 1024)
        _requested_seed = self._support.nested_nullable_int(request, "input", "seed")
        _text_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel",
            "",
        )
        requested_image_model = self._support.first_non_blank(
            self._support.nested_value(request, "model", "providerModel", ""),
            DEFAULT_OPENAI_IMAGE_MODEL,
        )
        _text_profile = self._resolve_text_profile(_text_model, _user_id)
        image_profile = self._resolve_media_profile(requested_image_model, GenerationModelKinds.IMAGE, _user_id)
        _applied_image_seed = _requested_seed if image_profile.get("supportsSeed", False) else None

        call_chain: list[dict[str, Any]] = []
        negative_prompt = self._build_negative_prompt(GenerationModelKinds.IMAGE)
        shaped_prompt = self._support.append_negative_prompt(prompt, negative_prompt)

        # Real image generation
        remote_image = await self._call_image_model(
            image_profile,
            shaped_prompt,
            width,
            height,
            reference_image_urls,
            _applied_image_seed,
        )
        image_artifact = self._support.write_binary_artifact(
            run_id,
            request,
            GenerationModelKinds.IMAGE,
            self._support.extension_from_mime_or_url(
                remote_image["mimeType"], str(remote_image.get("remoteSourceUrl", "")), GenerationModelKinds.IMAGE
            ),
            remote_image["data"],
        )

        call_chain.append(
            self._support.call_log(
                "generation",
                "image.generated",
                "success",
                "",
                {
                    "provider": remote_image["provider"],
                    "providerModel": remote_image["providerModel"],
                    "endpointHost": remote_image["endpointHost"],
                    "artifactWidth": image_artifact.get("width") or width,
                    "artifactHeight": image_artifact.get("height") or height,
                    "sourceWidth": image_artifact.get("sourceWidth") or 0,
                    "sourceHeight": image_artifact.get("sourceHeight") or 0,
                    "resizedToRequestedDimensions": bool(image_artifact.get("resizedToRequestedDimensions")),
                },
            )
        )
        artifact_width = int(image_artifact.get("width") or width)
        artifact_height = int(image_artifact.get("height") or height)

        artifact_public_url = image_artifact["publicUrl"]
        result: dict[str, Any] = {
            "runId": run_id,
            "kind": GenerationRunKinds.IMAGE,
            "prompt": prompt,
            "frameRole": frame_role,
            "keyframePrompt": prompt,
            "shapedPrompt": shaped_prompt,
            "negativePrompt": negative_prompt,
            "outputUrl": artifact_public_url,
            "mimeType": remote_image["mimeType"],
            "width": artifact_width,
            "height": artifact_height,
            "metadata": {
                "outputUrl": artifact_public_url,
                "fileUrl": artifact_public_url,
                "source": f"remote:{remote_image['providerModel']}",
                "remoteSourceUrl": artifact_public_url,
                "artifactRemoteSourceUrl": artifact_public_url,
                "providerRemoteSourceUrl": remote_image["remoteSourceUrl"],
                "frameRole": frame_role,
                "keyframePrompt": prompt,
                "textAnalysisProvider": _text_profile.get("provider", ""),
                "textAnalysisModel": _text_profile.get("modelName", ""),
                "keyframePromptProvider": _text_profile.get("provider", ""),
                "keyframePromptModel": _text_profile.get("modelName", ""),
                "promptRewriteProvider": _text_profile.get("provider", ""),
                "promptRewriteModel": _text_profile.get("modelName", ""),
                "promptRewriteSkipped": True,
                "referenceImageUrl": reference_image_url,
                "referenceImageUrls": reference_image_urls,
                "requestedSeed": _requested_seed,
                "imageGenerationSeed": _applied_image_seed,
                "watermark": False,
                "configSource": image_profile.get("source", ""),
                "provider": remote_image["provider"],
                "providerModel": remote_image["providerModel"],
                "requestedSize": remote_image["requestedSize"],
                "artifactWidth": artifact_width,
                "artifactHeight": artifact_height,
                "sourceWidth": int(image_artifact.get("sourceWidth") or 0),
                "sourceHeight": int(image_artifact.get("sourceHeight") or 0),
                "resizedToRequestedDimensions": bool(image_artifact.get("resizedToRequestedDimensions")),
                "providerRequest": remote_image["providerRequest"],
                "providerResponse": remote_image["providerResponse"],
                "providerHttpStatus": remote_image["httpStatus"],
                **self._request_metadata(request),
                "providerInteraction": {
                    "step": "image.generate",
                    "providerRequest": remote_image["providerRequest"],
                    "providerResponse": remote_image["providerResponse"],
                    "httpStatus": remote_image["httpStatus"],
                    "endpointHost": remote_image["endpointHost"],
                    "success": True,
                },
            },
            "modelInfo": self._support.build_media_model_info(
                _text_profile,
                None,
                None,
                image_profile,
                requested_image_model,
                GenerationModelKinds.IMAGE,
                None,
                None,
                remote_image["providerModel"],
                remote_image["endpointHost"],
                "",
                "spring-remote-image",
            ),
            "callChain": call_chain,
        }

        result["metadata"]["creditFeatureCode"] = "IMAGE_GENERATION"
        return self._support.run_envelope(run_id, GenerationRunKinds.IMAGE, request, result, "resultImage")

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
