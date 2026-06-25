# ruff: noqa: F811  # class method delegates to shared.py

"""Generation services — catalog, factory, run support, and application service.

Translates the Java classes:
- GenerationRunSupport
- GenerationRunFactory
- DefaultGenerationApplicationService

Wired up with real AI model providers:
- Text (LLM): OpenAiCompatibleTextModelProvider (DeepSeek, OpenAI, etc.)
- Image: OpenAI GPT Image API
- Video: SeedanceVideoModelProvider / AgnesVideoModelProvider

Provider config resolved from YAML files in config/model/.
Stub fallbacks remain for graceful degradation when config is missing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timezone
from typing import Any, Optional

from backend.config import settings
from backend.domain.generation_run import GenerationModelKinds, GenerationRunKinds, GenerationRunStatuses
from backend.infrastructure.generation_run_store import LocalGenerationRunStore
from backend.services.generation_artifacts import (
    GenerationArtifactStore,
    extension_from_mime_or_url,
)
from backend.services.generation_catalog_service import GenerationCatalogService
from backend.services.generation_payloads import (
    append_negative_prompt,
    build_media_model_info,
    build_model_info,
    build_negative_prompt,
    build_script_adjust_user_prompt,
    build_script_user_prompt,
    infer_camera_fixed,
)
from backend.services.generation_request_values import (
    find_nested_string,
    first_non_blank,
    map_value,
    nested_boolean,
    nested_int,
    nested_nullable_int,
    nested_string_list,
    nested_value,
    string_list,
    string_value,
)
from backend.services.model_config_service import (
    ModelRuntimeProfile,
    ModelRuntimePropertiesResolver,
)
from backend.shared import (
    find_nested_string,
    first_non_blank,
    first_positive_int,
    map_value,
    now_iso,
    positive_int,
    safe_bool,
    string_value,
    truncate_text,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Real model provider singletons (lazy-initialized to avoid circular imports)
# ---------------------------------------------------------------------------

_model_config_resolver = ModelRuntimePropertiesResolver(config_dir="./config")
_text_model_provider = None
_prompt_resolver = None


def _get_text_model_provider():
    global _text_model_provider
    if _text_model_provider is None:
        from backend.services.model_invocation import OpenAiCompatibleTextModelProvider
        _text_model_provider = OpenAiCompatibleTextModelProvider()
    return _text_model_provider


def _get_prompt_resolver():
    global _prompt_resolver
    if _prompt_resolver is None:
        from backend.services.model_invocation import PromptTemplateResolver
        _prompt_resolver = PromptTemplateResolver()
    return _prompt_resolver


_image_model_providers: list = []
_video_model_provider = None


def _get_image_model_providers():
    global _image_model_providers
    if not _image_model_providers:
        from backend.services.model_invocation import (
            ImageProviderTransport,
            OpenAiImageModelProvider,
        )
        transport = ImageProviderTransport()
        _image_model_providers = [
            OpenAiImageModelProvider(transport=transport),
        ]
    return _image_model_providers


def _get_video_model_provider():
    global _video_model_provider
    if _video_model_provider is None:
        from backend.services.model_invocation import (
            AgnesVideoModelProvider,
            CompositeVideoModelProvider,
            SeedanceVideoModelProvider,
            VideoProviderTransport,
        )
        transport = VideoProviderTransport()
        _video_model_provider = CompositeVideoModelProvider(
            providers=[
                SeedanceVideoModelProvider(transport=transport),
                AgnesVideoModelProvider(transport=transport),
            ]
        )
    return _video_model_provider

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


# ---------------------------------------------------------------------------
# Stub model providers (remote API calls are not the focus)
# ---------------------------------------------------------------------------

def _stub_text_response(text: str, model_name: str = "gpt-5.4") -> dict[str, Any]:
    return {
        "text": text,
        "modelName": model_name,
        "latencyMs": 120,
        "endpointHost": "api.stub.openai.com",
        "providerRequest": {"model": model_name, "messages": []},
        "providerResponse": {"choices": [{"message": {"content": text}}]},
        "httpStatus": 200,
        "responseId": f"stub-resp-{uuid.uuid4().hex[:12]}",
        "responsesApi": False,
    }


def _stub_image_result(
    provider_model: str = "stub-image-model",
    width: int = 1024,
    height: int = 1024,
) -> dict[str, Any]:
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal valid PNG header
    return {
        "provider": "stub",
        "providerModel": provider_model,
        "mimeType": "image/png",
        "data": data,
        "remoteSourceUrl": "",
        "endpointHost": "api.stub.image",
        "providerRequest": {"model": provider_model},
        "providerResponse": {},
        "httpStatus": 200,
        "requestedSize": f"{width}x{height}",
    }


def _stub_video_submission(
    provider_model: str = "stub-video-model",
) -> dict[str, Any]:
    return {
        "provider": "stub",
        "providerModel": provider_model,
        "taskId": f"stub-task-{uuid.uuid4().hex[:12]}",
        "endpointHost": "api.stub.video",
        "taskEndpointHost": "api.stub.video",
        "providerRequest": {"model": provider_model},
        "providerResponse": {"task_id": "stub-task-id"},
        "httpStatus": 200,
        "firstFrameUrl": "",
        "requestedLastFrameUrl": "",
        "returnLastFrame": True,
        "generateAudio": True,
    }


# ---------------------------------------------------------------------------
# GenerationRunSupport
# ---------------------------------------------------------------------------

# =============================================================================
# GENERATION RUN SUPPORT
# =============================================================================
class GenerationRunSupport:
    """Utility class providing helper methods for generation run orchestration.

    Mirrors the Java GenerationRunSupport.
    """

    def __init__(self) -> None:
        self._storage_root: str = getattr(settings, "storage_root", "./storage")
        self._artifact_store = GenerationArtifactStore(
            self._storage_root,
            getattr(settings, "web_origin", "http://127.0.0.1:80"),
        )

    # ── Run envelope ──────────────────────────────────────────────────

    def run_envelope(
        self,
        run_id: str,
        kind: str,
        request: dict[str, Any],
        result: dict[str, Any],
        specific_result_key: str,
        status: str = GenerationRunStatuses.SUCCEEDED,
    ) -> dict[str, Any]:
        now = self.now_iso()
        run: dict[str, Any] = {
            "id": run_id,
            "kind": kind,
            "status": status,
            "createdAt": now,
            "updatedAt": now,
            "input": self.map_value(request.get("input")),
            "model": self.map_value(request.get("model")),
            "options": self.map_value(request.get("options")),
            "storage": self.map_value(request.get("storage")),
            "auth": self.map_value(request.get("auth")),
            "result": result,
            specific_result_key: result,
        }
        return run

    def update_run_status(self, run: dict[str, Any], status: str) -> None:
        run["status"] = status
        run["updatedAt"] = self.now_iso()

    # ── Nested value accessors ───────────────────────────────────────

    def nested_value(
        self, payload: dict[str, Any], parent_key: str, child_key: str, default: str = ""
    ) -> str:
        return nested_value(payload, parent_key, child_key, default)

    def nested_string_list(
        self, payload: dict[str, Any], parent_key: str, child_key: str
    ) -> list[str]:
        return nested_string_list(payload, parent_key, child_key)

    def nested_int(
        self, payload: dict[str, Any], parent_key: str, child_key: str, default: int = 0
    ) -> int:
        return nested_int(payload, parent_key, child_key, default)

    def nested_nullable_int(
        self, payload: dict[str, Any], parent_key: str, child_key: str
    ) -> int | None:
        return nested_nullable_int(payload, parent_key, child_key)

    def nested_boolean(
        self, payload: dict[str, Any], parent_key: str, child_key: str, default: bool = False
    ) -> bool:
        return nested_boolean(payload, parent_key, child_key, default)

    def map_value(self, value: Any) -> dict[str, Any]:
        return map_value(value)

    def string_value(self, value: Any) -> str:
        return string_value(value)

    def first_non_blank(self, *values: str) -> str:
        return first_non_blank(*values)

    def find_nested_string(self, value: Any, *keys: str) -> str:
        return find_nested_string(value, *keys)

    def required_model(self, value: str, field_name: str, label: str) -> str:
        normalized = value.strip() if value else ""
        if normalized:
            return normalized
        raise ValueError(f"请先选择{label}（{field_name}）")

    def now_iso(self) -> str:
        return now_iso()

    def truncate_text(self, value: str, limit: int) -> str:
        return truncate_text(value, limit)

    def strip_markdown_fence(self, text: str) -> str:
        value = text.strip() if text else ""
        if not value.startswith("```"):
            return value
        first_break = value.find("\n")
        last_fence = value.rfind("```")
        if first_break < 0 or last_fence <= first_break:
            return value.replace("```", "").strip()
        return value[first_break + 1 : last_fence].strip()

    def bounded_temperature(self, value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    def positive_int(self, raw: str, fallback: int) -> int:
        return positive_int(raw, fallback)

    def first_positive_int(self, *values: int) -> int:
        return first_positive_int(*values)

    def normalize_value(self, value: str) -> str:
        return value.strip().lower() if value else ""

    def normalize_frame_role(self, frame_role: str) -> str:
        return "last" if self.string_value(frame_role).lower() == "last" else "first"

    def parse_dimensions(
        self, raw: str, fallback_width: int, fallback_height: int
    ) -> tuple[int, int]:
        normalized = raw.strip().lower().replace("x", "*") if raw else ""
        parts = normalized.split("*")
        if len(parts) == 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except (ValueError, TypeError):
                pass
        return (fallback_width, fallback_height)

    def extension_from_mime_or_url(self, mime_type: str, source_url: str, media_type: str) -> str:
        return extension_from_mime_or_url(mime_type, source_url, media_type)

    def append_negative_prompt(self, prompt: str, negative_prompt: str) -> str:
        return append_negative_prompt(prompt, negative_prompt)

    def infer_camera_fixed(self, prompt: str, fallback: bool) -> bool:
        return infer_camera_fixed(prompt, fallback)

    def storage_relative_dir(self, request: dict[str, Any], run_id: str) -> str:
        return self._artifact_store.storage_relative_dir(request, run_id)

    def storage_file_stem(self, request: dict[str, Any], fallback: str) -> str:
        return self._artifact_store.storage_file_stem(request, fallback)

    def storage_file_name(self, request: dict[str, Any], fallback: str) -> str:
        return self._artifact_store.storage_file_name(request, fallback)

    def string_list(self, value: Any) -> list[str]:
        return string_list(value)

    def integer_list(self, value: Any) -> list[int]:
        if isinstance(value, list):
            result: list[int] = []
            for item in value:
                p = self.positive_int(str(item) if item is not None else "", 0)
                if p > 0:
                    result.append(p)
            return result
        return []

    def parse_string_list(self, raw: str, fallback: list[str]) -> list[str]:
        items = [p.strip() for p in raw.split(",") if p and p.strip()] if raw else []
        return items if items else fallback

    def parse_integer_list(self, raw: str, fallback: list[int]) -> list[int]:
        items = [self.positive_int(p, 0) for p in raw.split(",") if p and p.strip()] if raw else []
        return [i for i in items if i > 0] if [i for i in items if i > 0] else fallback

    # ── Call log ─────────────────────────────────────────────────────

    def call_log(
        self, stage: str, event: str, status: str, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        safe = {}
        if details:
            for k, v in details.items():
                if v is not None:
                    safe[k] = v
        if "source" not in safe:
            safe["source"] = "python"
        return {
            "timestamp": self.now_iso(),
            "stage": stage,
            "event": event,
            "status": status,
            "message": message,
            "details": safe,
        }

    # ── Model info builders ──────────────────────────────────────────

    def build_model_info(
        self,
        profile: dict[str, Any],
        requested_model: str,
        media_kind: str,
        response: dict[str, Any] | None,
        source_tag: str,
    ) -> dict[str, Any]:
        return build_model_info(profile, requested_model, media_kind, response, source_tag)

    def build_media_model_info(
        self,
        text_profile: dict[str, Any],
        rewrite_profile: dict[str, Any] | None,
        vision_profile: dict[str, Any] | None,
        media_profile: dict[str, Any],
        requested_model: str,
        media_kind: str,
        text_response: dict[str, Any] | None,
        vision_response: dict[str, Any] | None,
        resolved_model: str,
        endpoint_host: str,
        task_endpoint_host: str,
        source_tag: str,
    ) -> dict[str, Any]:
        return build_media_model_info(
            text_profile,
            rewrite_profile,
            vision_profile,
            media_profile,
            requested_model,
            media_kind,
            text_response,
            vision_response,
            resolved_model,
            endpoint_host,
            task_endpoint_host,
            source_tag,
        )

    # ── Artifact helpers (stub — writes to local storage) ────────────

    def write_text_artifact(
        self, run_id: str, request: dict[str, Any], file_name: str, content: str
    ) -> dict[str, Any]:
        return self._artifact_store.write_text_artifact(run_id, request, file_name, content)

    def write_binary_artifact(
        self,
        run_id: str,
        request: dict[str, Any],
        file_stem: str,
        extension: str,
        data: bytes,
    ) -> dict[str, Any]:
        return self._artifact_store.write_binary_artifact(run_id, request, file_stem, extension, data)

    def materialize_binary_artifact(
        self, run_id: str, relative_dir: str, file_stem: str, source_url: str
    ) -> dict[str, Any]:
        return self._artifact_store.materialize_binary_artifact(run_id, relative_dir, file_stem, source_url)

    def build_externally_accessible_url(self, public_url: str) -> str:
        return self._artifact_store.build_externally_accessible_url(public_url)

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        return self._artifact_store.image_data_uri_from_public_url(public_url)


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

    _VIDEO_SUCCESS_STATES = {"SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED"}
    _VIDEO_FAILED_STATES = {"FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR"}

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
        self._config_resolver = config_resolver or _model_config_resolver
        self._text_provider = text_provider or _get_text_model_provider()
        self._prompt_resolver = prompt_resolver or _get_prompt_resolver()
        self._image_providers = image_providers or _get_image_model_providers()
        self._video_provider = video_provider or _get_video_model_provider()

    # ------------------------------------------------------------------
    # Public creation methods
    # ------------------------------------------------------------------

    async def create_probe_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        _user_id = self._user_id_from_request(request)
        requested_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel",
            "",
        )
        profile = self._resolve_text_profile(requested_model, _user_id)
        call_chain: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {
            "requestedModel": requested_model,
            "resolvedModel": profile.get("modelName", ""),
            "provider": profile.get("provider", ""),
            "family": GenerationModelKinds.TEXT,
            "mode": "probe",
            "endpointHost": profile.get("endpointHost", ""),
            "checkedAt": self._support.now_iso(),
            "configSource": profile.get("source", ""),
        }

        if not profile.get("ready", True):
            metadata["latencyMs"] = 0
            metadata["messagePreview"] = "text model config missing"
            call_chain.append(
                self._support.call_log("probe", "probe.config_missing", "error", "", {"source": profile.get("source", "")})
            )
            result: dict[str, Any] = {
                "runId": run_id,
                "kind": GenerationRunKinds.PROBE,
                "ready": False,
                "latencyMs": 0,
                "callChain": call_chain,
                "metadata": metadata,
            }
            return self._support.run_envelope(run_id, GenerationRunKinds.PROBE, request, result, "resultProbe")

        # Call real text model
        response = await self._call_text_model(
            profile,
            system_prompt="You are a connectivity probe. Respond with OK.",
            user_prompt="OK",
        )
        metadata["latencyMs"] = response["latencyMs"]
        metadata["endpointHost"] = response["endpointHost"]
        metadata["messagePreview"] = self._support.truncate_text(response["text"], 80)
        metadata["providerRequest"] = response["providerRequest"]
        metadata["providerResponse"] = response["providerResponse"]
        metadata["providerHttpStatus"] = response["httpStatus"]
        metadata["providerInteraction"] = self._text_provider_interaction("probe", response)
        call_chain.append(
            self._support.call_log("probe", "probe.completed", "success", "", {
                "latencyMs": response["latencyMs"],
                "responsesApi": response["responsesApi"],
            })
        )
        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.PROBE,
            "ready": True,
            "latencyMs": response["latencyMs"],
            "callChain": call_chain,
            "metadata": metadata,
        }
        return self._support.run_envelope(run_id, GenerationRunKinds.PROBE, request, result, "resultProbe")

    async def create_script_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        _user_id = self._user_id_from_request(request)
        source_text = self._support.nested_value(request, "input", "text", "")
        visual_style = self._support.nested_value(request, "options", "visualStyle", "")
        requested_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel", "",
        )
        profile = self._resolve_text_profile(requested_model, _user_id)
        if not source_text.strip():
            raise ValueError("")

        prompt = self._build_script_user_prompt(source_text, visual_style)
        call_chain: list[dict[str, Any]] = []
        provider_interactions: list[dict[str, Any]] = []

        # Real draft call
        system_prompt = self._prompt_resolver.system_prompt("script", "short_drama_script")
        draft_response = await self._call_text_model(
            profile,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        draft_script_markdown = self._support.strip_markdown_fence(draft_response["text"])
        provider_interactions.append(self._text_provider_interaction("draft", draft_response))
        call_chain.append(
            self._support.call_log("script", "script.requested", "success", "", {
                "provider": profile.get("provider", ""),
                "modelName": profile.get("modelName", ""),
                "endpointHost": draft_response["endpointHost"],
            })
        )
        call_chain.append(
            self._support.call_log("script", "script.draft_completed", "success", "", {
                "latencyMs": draft_response["latencyMs"],
                "responsesApi": draft_response["responsesApi"],
                "responseId": draft_response["responseId"],
            })
        )

        script_markdown = draft_script_markdown
        final_response = draft_response
        review_applied = False
        review_fallback_reason = ""

        # Real review call
        review_system_prompt = system_prompt + "\n\nPlease review and improve the script above for quality and completeness."
        review_response = await self._call_text_model(
            profile,
            system_prompt=review_system_prompt,
            user_prompt=draft_script_markdown,
        )
        provider_interactions.append(self._text_provider_interaction("review", review_response))
        call_chain.append(
            self._support.call_log("script", "script.review_requested", "success", "", {
                "provider": profile.get("provider", ""),
                "modelName": profile.get("modelName", ""),
                "endpointHost": review_response["endpointHost"],
            })
        )
        reviewed_script = self._support.strip_markdown_fence(review_response["text"])
        invalid_reason = self._invalid_storyboard_reason(reviewed_script)
        if not invalid_reason:
            script_markdown = reviewed_script
            final_response = review_response
            review_applied = True
        else:
            review_fallback_reason = invalid_reason
            call_chain.append(
                self._support.call_log("script", "script.review_fallback", "warning", "", {
                    "reason": invalid_reason,
                    "responseId": review_response["responseId"],
                })
            )

        call_chain.append(
            self._support.call_log("script", "script.completed", "success",
                "" if review_applied else "",
                {
                    "latencyMs": final_response["latencyMs"],
                    "responsesApi": final_response["responsesApi"],
                    "responseId": final_response["responseId"],
                    "reviewApplied": review_applied,
                }
            )
        )

        artifact = self._support.write_text_artifact(run_id, request, "script.md", script_markdown)
        model_info = self._support.build_model_info(profile, requested_model, "script", final_response, "spring-text-script")

        metadata = {
            "visualStyle": visual_style,
            "draftScriptMarkdown": draft_script_markdown,
            "scriptMarkdown": script_markdown,
            "reviewApplied": review_applied,
            "draftResponseId": draft_response["responseId"],
            "reviewResponseId": review_response["responseId"],
            "finalResponseId": final_response["responseId"],
            "providerInteractions": provider_interactions,
            "providerRequest": final_response["providerRequest"],
            "providerResponse": final_response["providerResponse"],
            "providerHttpStatus": final_response["httpStatus"],
            "fileUrl": artifact["publicUrl"],
            "configSource": profile.get("source", ""),
            **self._request_metadata(request),
        }
        if review_fallback_reason:
            metadata["reviewFallbackReason"] = review_fallback_reason

        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.SCRIPT,
            "sourceText": source_text,
            "visualStyle": visual_style,
            "prompt": prompt,
            "outputFormat": "markdown",
            "scriptMarkdown": script_markdown,
            "markdownPath": artifact["absolutePath"],
            "markdownUrl": artifact["publicUrl"],
            "mimeType": "text/markdown",
            "callChain": call_chain,
            "metadata": metadata,
            "modelInfo": model_info,
        }
        return self._support.run_envelope(run_id, GenerationRunKinds.SCRIPT, request, result, "resultScript")

    async def create_script_adjust_run(self, run_id: str, request: dict[str, Any]) -> dict[str, Any]:
        _user_id = self._user_id_from_request(request)
        source_text = self._support.first_non_blank(
            self._support.nested_value(request, "input", "text", ""),
            self._support.nested_value(request, "input", "sourceText", ""),
        )
        script_markdown = self._support.nested_value(request, "input", "scriptMarkdown", "")
        adjustment_prompt = self._support.nested_value(request, "input", "adjustmentPrompt", "")
        visual_style = self._support.nested_value(request, "options", "visualStyle", "")
        requested_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel", "",
        )
        profile = self._resolve_text_profile(requested_model, self._user_id_from_request(request))
        if not script_markdown.strip():
            raise ValueError("")

        prompt = self._build_script_adjust_user_prompt(source_text, visual_style, script_markdown, adjustment_prompt)
        call_chain: list[dict[str, Any]] = []
        provider_interactions: list[dict[str, Any]] = []

        # Real adjust call
        adjust_system_prompt = self._prompt_resolver.system_prompt("script", "short_drama_script")
        adjust_response = await self._call_text_model(
            profile,
            system_prompt=adjust_system_prompt,
            user_prompt=prompt,
        )
        provider_interactions.append(self._text_provider_interaction("adjust", adjust_response))
        call_chain.append(
            self._support.call_log("script", "script.adjust_requested", "success", "", {
                "provider": profile.get("provider", ""),
                "modelName": profile.get("modelName", ""),
                "endpointHost": adjust_response["endpointHost"],
            })
        )

        adjusted_script = self._support.strip_markdown_fence(adjust_response["text"])
        invalid_reason = self._invalid_storyboard_reason(adjusted_script)
        if invalid_reason:
            call_chain.append(
                self._support.call_log("script", "script.adjust_invalid", "error", "", {
                    "reason": invalid_reason,
                    "responseId": adjust_response["responseId"],
                })
            )
            raise ValueError(f"  {invalid_reason}")

        call_chain.append(
            self._support.call_log("script", "script.adjust_completed", "success", "", {
                "latencyMs": adjust_response["latencyMs"],
                "responsesApi": adjust_response["responsesApi"],
                "responseId": adjust_response["responseId"],
                "adjustmentMode": "self_review" if not adjustment_prompt.strip() else "user_prompt",
            })
        )

        artifact = self._support.write_text_artifact(run_id, request, "script.md", adjusted_script)
        model_info = self._support.build_model_info(profile, requested_model, "script", adjust_response, "spring-text-script-adjust")

        adjustment_mode = "self_review" if not adjustment_prompt.strip() else "user_prompt"
        metadata = {
            "visualStyle": visual_style,
            "scriptMarkdown": adjusted_script,
            "sourceScriptMarkdown": script_markdown,
            "adjustmentPrompt": adjustment_prompt,
            "adjustmentMode": adjustment_mode,
            "adjustmentResponseId": adjust_response["responseId"],
            "providerInteractions": provider_interactions,
            "providerRequest": adjust_response["providerRequest"],
            "providerResponse": adjust_response["providerResponse"],
            "providerHttpStatus": adjust_response["httpStatus"],
            "fileUrl": artifact["publicUrl"],
            "configSource": profile.get("source", ""),
            **self._request_metadata(request),
        }

        result = {
            "runId": run_id,
            "kind": GenerationRunKinds.SCRIPT_ADJUST,
            "sourceText": source_text,
            "visualStyle": visual_style,
            "prompt": prompt,
            "adjustmentPrompt": adjustment_prompt,
            "adjustmentMode": adjustment_mode,
            "outputFormat": "markdown",
            "scriptMarkdown": adjusted_script,
            "markdownPath": artifact["absolutePath"],
            "markdownUrl": artifact["publicUrl"],
            "mimeType": "text/markdown",
            "callChain": call_chain,
            "metadata": metadata,
            "modelInfo": model_info,
        }
        return self._support.run_envelope(run_id, GenerationRunKinds.SCRIPT_ADJUST, request, result, "resultScript")

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
        _style_preset = self._support.nested_value(request, "options", "stylePreset", "cinematic")
        _text_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel", "",
        )
        requested_image_model = self._support.required_model(
            self._support.nested_value(request, "model", "providerModel", ""),
            "providerModel", "",
        )
        _text_profile = self._resolve_text_profile(_text_model, _user_id)
        image_profile = self._resolve_media_profile(requested_image_model, GenerationModelKinds.IMAGE, _user_id)
        _applied_image_seed = _requested_seed if image_profile.get("supportsSeed", False) else None

        call_chain: list[dict[str, Any]] = []
        negative_prompt = self._build_negative_prompt(GenerationModelKinds.IMAGE)
        shaped_prompt = self._support.append_negative_prompt(prompt, negative_prompt)

        # Real image generation
        remote_image = await self._call_image_model(
            image_profile, shaped_prompt, width, height,
            reference_image_urls, _applied_image_seed,
        )
        image_artifact = self._support.write_binary_artifact(
            run_id, request, GenerationModelKinds.IMAGE,
            self._support.extension_from_mime_or_url(
                remote_image["mimeType"], str(remote_image.get("remoteSourceUrl", "")), GenerationModelKinds.IMAGE
            ),
            remote_image["data"],
        )

        call_chain.append(
            self._support.call_log("generation", "image.generated", "success", "", {
                "provider": remote_image["provider"],
                "providerModel": remote_image["providerModel"],
                "endpointHost": remote_image["endpointHost"],
            })
        )

        result: dict[str, Any] = {
            "runId": run_id,
            "kind": GenerationRunKinds.IMAGE,
            "prompt": prompt,
            "frameRole": frame_role,
            "keyframePrompt": prompt,
            "shapedPrompt": shaped_prompt,
            "negativePrompt": negative_prompt,
            "outputUrl": image_artifact["publicUrl"],
            "mimeType": remote_image["mimeType"],
            "width": width,
            "height": height,
            "metadata": {
                "stylePreset": _style_preset,
                "outputUrl": image_artifact["publicUrl"],
                "fileUrl": image_artifact["publicUrl"],
                "source": f"remote:{remote_image['providerModel']}",
                "remoteSourceUrl": remote_image["remoteSourceUrl"],
                "artifactRemoteSourceUrl": self._support.build_externally_accessible_url(image_artifact["publicUrl"]),
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
                _text_profile, None, None, image_profile, requested_image_model,
                GenerationModelKinds.IMAGE, None, None,
                remote_image["providerModel"], remote_image["endpointHost"], "",
                "spring-remote-image",
            ),
            "callChain": call_chain,
        }

        result["metadata"]["creditFeatureCode"] = "IMAGE_GENERATION"
        return self._support.run_envelope(run_id, GenerationRunKinds.IMAGE, request, result, "resultImage")

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
        _style_preset = self._support.nested_value(request, "options", "stylePreset", "cinematic")
        _text_model = self._support.required_model(
            self._support.nested_value(request, "model", "textAnalysisModel", ""),
            "textAnalysisModel", "",
        )
        requested_video_model = self._support.required_model(
            self._support.nested_value(request, "model", "providerModel", ""),
            "providerModel", "",
        )
        video_profile = self._resolve_media_profile(requested_video_model, GenerationModelKinds.VIDEO, _user_id)
        duration = self._normalize_video_duration(video_profile, _requested_duration, _requested_min_duration, _requested_max_duration)

        _first_frame_url = self._resolve_video_frame_input(
            self._support.nested_value(request, "input", "firstFrameUrl", ""), "firstFrameUrl"
        )
        _last_frame_url = self._resolve_video_frame_input(
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
            video_profile, shaped_prompt, w, h, duration,
            _first_frame_url, _last_frame_url, _applied_video_seed,
            _camera_fixed, _watermark, _return_last_frame, _generate_audio,
        )
        provider_interactions.append({
            "step": "video.submit",
            "providerRequest": submission["providerRequest"],
            "providerResponse": submission["providerResponse"],
            "httpStatus": submission["httpStatus"],
            "endpointHost": submission["endpointHost"],
            "success": True,
        })

        call_chain.append(
            self._support.call_log("generation", "video.submitted", "running", "", {
                "provider": submission["provider"],
                "providerModel": submission["providerModel"],
                "taskId": submission["taskId"],
                "endpointHost": submission["endpointHost"],
                "taskEndpointHost": submission["taskEndpointHost"],
            })
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
                _text_profile, None, None, video_profile, requested_video_model,
                GenerationModelKinds.VIDEO, None, None,
                submission["providerModel"], submission["endpointHost"], submission["taskEndpointHost"],
                "spring-remote-video-async",
            ),
            "callChain": call_chain,
        }

        return self._support.run_envelope(run_id, GenerationRunKinds.VIDEO, request, result, "resultVideo", GenerationRunStatuses.RUNNING)

    async def refresh_video_run(self, run: dict[str, Any]) -> dict[str, Any]:
        kind = self._support.string_value(run.get("kind"))
        if kind.lower() != GenerationRunKinds.VIDEO:
            return run
        status = self._support.string_value(run.get("status")).lower()
        if not GenerationRunStatuses.is_active(status):
            return run
        result = self._support.map_value(run.get("result"))
        if not result:
            return run
        metadata = self._support.map_value(result.get("metadata"))
        task_id = self._support.string_value(metadata.get("taskId"))
        requested_model = self._support.first_non_blank(
            self._support.string_value(metadata.get("requestedModel")),
            self._support.string_value(metadata.get("providerModel")),
        )
        if not task_id or not requested_model:
            return run
        next_poll_at = metadata.get("nextPollAt", 0)
        now_ms = datetime.now(UTC).timestamp() * 1000
        if isinstance(next_poll_at, (int, float)) and next_poll_at > now_ms:
            return run

        _user_id = self._user_id_from_run(run)
        _profile_dict = self._resolve_media_profile(requested_model, GenerationModelKinds.VIDEO, _user_id)
        call_chain = self._mutable_call_chain(result.get("callChain"))

        # Real video task query
        try:
            query_result = await self._call_video_query(_profile_dict, task_id)
            query_status = query_result["taskStatus"]
            video_url = query_result["videoUrl"]
            task_message = self._support.string_value(query_result.get("taskMessage"))
            provider_response = query_result.get("providerResponse", {})
            provider_request = query_result.get("providerRequest", {"task_id": task_id})
            query_http_status = query_result.get("httpStatus", 200)
        except Exception as ex:
            logger.warning("Video task query failed for %s: %s", task_id, ex)
            query_status = "UNKNOWN"
            video_url = ""
            task_message = str(ex)
            # Preserve provider response from GenerationProviderException for
            # permanent-error detection (quota, billing, auth, etc.).
            _ex_provider_response = getattr(ex, "provider_response", None)
            provider_response = _ex_provider_response if _ex_provider_response is not None else {"error": task_message}
            provider_request = {"task_id": task_id}
            query_http_status = getattr(ex, "http_status", 0)

        # Detect permanent provider errors (quota, billing, auth, etc.) and fail
        # the run immediately instead of continuing to poll.
        from backend.domain.video_run_monitor import is_permanent_provider_error
        if is_permanent_provider_error(task_message, provider_response):
            error_msg = self._support.first_non_blank(
                task_message,
                self._support.find_nested_string(provider_response, "message", "error", "reason", "detail"),
                query_status,
            )
            result["error"] = error_msg
            metadata["taskStatus"] = "FAILED"
            metadata["taskMessage"] = task_message
            metadata["error"] = error_msg
            metadata["providerPayload"] = provider_response
            metadata["nextPollAt"] = None
            self._append_provider_query_history(metadata, {
                "step": "video.query",
                "providerRequest": provider_request,
                "providerResponse": provider_response,
                "httpStatus": query_http_status,
                "endpointHost": _profile_dict.get("taskEndpointHost", ""),
                "success": False,
            })
            call_chain.append(
                self._support.call_log("generation", "video.failed", "error", "", {
                    "taskId": task_id,
                    "status": "FAILED",
                    "error": error_msg,
                    "reason": "permanent_provider_error",
                })
            )
            result["callChain"] = call_chain
            result["metadata"] = metadata
            run["result"] = result
            run["resultVideo"] = result
            self._support.update_run_status(run, GenerationRunStatuses.FAILED)
            return run

        metadata["taskStatus"] = query_status
        metadata["taskMessage"] = task_message
        metadata["providerPayload"] = provider_response
        self._append_provider_query_history(metadata, {
            "step": "video.query",
            "providerRequest": provider_request,
            "providerResponse": provider_response,
            "httpStatus": query_http_status,
            "endpointHost": _profile_dict.get("taskEndpointHost", ""),
            "success": query_status in self._VIDEO_SUCCESS_STATES,
        })

        if query_status in self._VIDEO_SUCCESS_STATES:
            relative_dir = self._support.first_non_blank(
                self._support.string_value(metadata.get("storageRelativeDir")),
                f"gen/_runs/{self._support.string_value(run.get('id'))}",
            )
            file_stem = self._support.first_non_blank(
                self._support.string_value(metadata.get("storageFileStem")), "video"
            )
            artifact = self._support.materialize_binary_artifact(
                self._support.string_value(run.get("id")), relative_dir, file_stem, video_url
            )
            result["outputUrl"] = artifact["publicUrl"]
            result["mimeType"] = artifact["mimeType"]
            result["hasAudio"] = self._support.nested_boolean({"meta": metadata}, "meta", "generateAudio", True)
            metadata["outputUrl"] = artifact["publicUrl"]
            metadata["fileUrl"] = artifact["publicUrl"]
            metadata["remoteSourceUrl"] = video_url
            metadata["providerLastFrameUrl"] = ""
            metadata["lastFrameUrl"] = self._support.first_non_blank(
                "", self._support.string_value(metadata.get("requestedLastFrameUrl"))
            )
            metadata["last_frame_url"] = metadata["lastFrameUrl"]
            metadata["nextPollAt"] = None
            call_chain.append(
                self._support.call_log("generation", "video.completed", "success", "", {
                    "taskId": task_id,
                    "status": query_status,
                    "outputUrl": artifact["publicUrl"],
                })
            )
            result["callChain"] = call_chain
            result["metadata"] = metadata
            run["result"] = result
            run["resultVideo"] = result
            self._support.update_run_status(run, GenerationRunStatuses.SUCCEEDED)
            return run

        if query_status in self._VIDEO_FAILED_STATES:
            error_msg = self._support.first_non_blank(
                task_message,
                self._support.find_nested_string(provider_response, "message", "error", "reason", "detail"),
                query_status,
            )
            result["error"] = error_msg
            metadata["error"] = error_msg
            metadata["nextPollAt"] = None
            call_chain.append(
                self._support.call_log("generation", "video.failed", "error", "", {
                    "taskId": task_id,
                    "status": query_status,
                    "error": error_msg,
                })
            )
            result["callChain"] = call_chain
            result["metadata"] = metadata
            run["result"] = result
            run["resultVideo"] = result
            self._support.update_run_status(run, GenerationRunStatuses.FAILED)
            return run

        metadata["nextPollAt"] = now_ms + 5000
        call_chain.append(
            self._support.call_log("generation", "video.polling", "running", "", {
                "taskId": task_id,
                "status": query_status,
            })
        )
        result["callChain"] = call_chain
        result["metadata"] = metadata
        run["result"] = result
        run["resultVideo"] = result
        self._support.update_run_status(run, GenerationRunStatuses.RUNNING)
        return run

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_text_profile(self, requested_model: str, user_id: int | None = None) -> dict[str, Any]:
        """Resolve text model profile using the real config resolver."""
        try:
            profile = self._config_resolver.resolve_text_profile(requested_model, user_id)
            return {
                "userId": user_id,
                "requestedModel": requested_model,
                "modelName": profile.config.provider_model or requested_model,
                "provider": profile.provider,
                "endpointHost": profile.endpoint_host,
                "taskEndpointHost": "",
                "source": profile.source,
                "ready": profile.ready,
                "temperature": profile.config.temperature,
                "maxTokens": profile.config.max_tokens,
                "supportsSeed": profile.supports_seed(),
                "cameraFixed": False,
                "watermark": False,
                "supportedDurations": [],
                "pollIntervalSeconds": 5,
            }
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
            return {
                "userId": user_id,
                "requestedModel": requested_model,
                "modelName": profile.config.provider_model or requested_model,
                "provider": profile.provider,
                "endpointHost": profile.endpoint_host,
                "taskEndpointHost": profile.task_endpoint_host,
                "source": profile.source,
                "ready": profile.ready,
                "temperature": 0.3,
                "maxTokens": 4096,
                "supportsSeed": profile.supports_seed(),
                "cameraFixed": profile.capabilities.camera_fixed,
                "watermark": profile.capabilities.watermark,
                "supportedDurations": profile.supported_durations(),
                "pollIntervalSeconds": profile.capabilities.poll_interval_seconds,
            }
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

        raise GenerationConfigurationException(
            f"no image provider found for provider={profile.config.provider}"
        )

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
        return {
            "modelName": requested_model if requested_model else "gpt-5.4",
            "provider": "openai",
            "endpointHost": "api.stub.openai.com",
            "taskEndpointHost": "",
            "source": "python-stub",
            "ready": True,
            "temperature": 0.3,
            "maxTokens": 4096,
            "supportsSeed": False,
            "cameraFixed": False,
            "watermark": False,
            "supportedDurations": [],
            "pollIntervalSeconds": 5,
        }

    @staticmethod
    def _stub_resolve_media_profile(
        requested_model: str, media_kind: str
    ) -> dict[str, Any]:
        return {
            "modelName": requested_model if requested_model else f"stub-{media_kind}",
            "provider": "stub",
            "endpointHost": f"api.stub.{media_kind}",
            "taskEndpointHost": f"api.stub.{media_kind}",
            "source": "python-stub",
            "ready": True,
            "temperature": 0.3,
            "maxTokens": 4096,
            "supportsSeed": True,
            "cameraFixed": False,
            "watermark": False,
            "supportedDurations": [4, 5, 6, 8, 10, 12, 15],
            "pollIntervalSeconds": 5,
        }

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
    def _user_id_from_run(run: dict[str, Any]) -> int | None:
        request = run.get("request")
        if isinstance(request, dict):
            user_id = GenerationRunFactory._user_id_from_request(request)
            if user_id is not None:
                return user_id
        user_id = GenerationRunFactory._user_id_from_request(run)
        if user_id is not None:
            return user_id
        for key in ("resultVideo", "result"):
            result = run.get(key)
            if not isinstance(result, dict):
                continue
            metadata = result.get("metadata")
            if not isinstance(metadata, dict):
                continue
            uid = metadata.get("userId")
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
    def _build_script_user_prompt(source_text: str, visual_style: str) -> str:
        return build_script_user_prompt(source_text, visual_style)

    @staticmethod
    def _build_script_adjust_user_prompt(
        source_text: str, visual_style: str, source_script: str, adjustment_prompt: str
    ) -> str:
        return build_script_adjust_user_prompt(source_text, visual_style, source_script, adjustment_prompt)

    @staticmethod
    def _stub_script_output(source_text: str, visual_style: str) -> str:
        return (
            "【 】\n-  : \n\n【 】\n|  |  |  |  |  |\n| --- | --- | --- | --- | --- |\n| 1 | ... | ... | ... | 5 |"
        )

    @staticmethod
    def _invalid_storyboard_reason(storyboard: str) -> str:
        if not storyboard or not storyboard.strip():
            return "review output is blank"
        if "【 】" not in storyboard and "【 " not in storyboard:
            return "review output missing character definitions"
        if "【 】" not in storyboard:
            return "review output missing storyboard section"
        return ""

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

    @staticmethod
    def _resolve_video_frame_input(url: str, field_name: str) -> str:
        normalized = url.strip() if url else ""
        if not normalized:
            return ""
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        if normalized.startswith("data:image/") and ";base64," in normalized:
            return normalized
        return ""

    def _text_provider_interaction(
        self, step: str, response: dict[str, Any]
    ) -> dict[str, Any]:
        interaction = {
            "step": step,
            "providerRequest": response.get("providerRequest", {}),
            "providerResponse": response.get("providerResponse", {}),
            "httpStatus": response.get("httpStatus", 0),
            "endpointHost": response.get("endpointHost", ""),
            "success": True,
        }
        if response.get("httpStatus", 0) == 0 or (200 <= response.get("httpStatus", 0) < 300):
            interaction["success"] = True
        else:
            interaction["success"] = False
        interaction["responseId"] = response.get("responseId", "")
        interaction["responsesApi"] = response.get("responsesApi", False)
        interaction["latencyMs"] = response.get("latencyMs", 0)
        return interaction

    @staticmethod
    def _append_provider_query_history(
        metadata: dict[str, Any], interaction: dict[str, Any]
    ) -> None:
        history: list[dict[str, Any]] = []
        raw = metadata.get("providerQueryHistory")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    history.append(dict(item))
        history.append(interaction)
        metadata["providerQueryHistory"] = history

    @staticmethod
    def _mutable_call_chain(raw: Any) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    items.append(dict(item))
        return items


# ===========================================================================
# DefaultGenerationApplicationService
# ===========================================================================

# =============================================================================
# APPLICATION SERVICE
# =============================================================================
class DefaultGenerationApplicationService:
    """Main generation service combining catalog, factory, and run store.

    Mirrors the Java DefaultGenerationApplicationService.
    """

    def __init__(
        self,
        generation_run_store: LocalGenerationRunStore | None = None,
        catalog_service: GenerationCatalogService | None = None,
        generation_run_factory: GenerationRunFactory | None = None,
        support: GenerationRunSupport | None = None,
        config_resolver: ModelRuntimePropertiesResolver | None = None,
    ) -> None:
        self._store = generation_run_store or LocalGenerationRunStore()
        self._catalog_service = catalog_service or GenerationCatalogService()
        self._factory = generation_run_factory or GenerationRunFactory(
            support or GenerationRunSupport(),
            config_resolver=config_resolver,
        )
        self._support = support or GenerationRunSupport()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def catalog(self) -> dict[str, Any]:
        """Return the available generation catalog."""
        return self._catalog_service.catalog()

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Synchronously create a generation run."""
        run_id = f"run_{uuid.uuid4().hex}"
        kind = str(request.get("kind", GenerationRunKinds.PROBE))
        return await self._create_run_by_kind_and_persist(run_id, kind, request)

    async def create_async_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create an async generation run (returns immediately with ACCEPTED status)."""
        run_id = f"run_{uuid.uuid4().hex}"
        kind = str(request.get("kind", GenerationRunKinds.PROBE))

        # Probe runs are always synchronous
        if kind.lower() == GenerationRunKinds.PROBE:
            return await self._create_run_by_kind_and_persist(run_id, kind, request)

        self._validate_supported_kind(kind)

        accepted = self._accepted_run(run_id, kind, request)
        self._runs_cache[run_id] = accepted
        await self._store.save(run_id, accepted)

        # Fire and forget the background execution
        asyncio.create_task(self._execute_async_run(run_id, kind, request))

        return accepted

    async def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent generation runs."""
        return await self._store.list(limit)

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a single generation run by ID, refreshing if it's a video run."""
        run = self._runs_cache.get(run_id)
        if run is None:
            run = await self._store.get(run_id)
        if run is None:
            raise GenerationRunNotFoundException(run_id)

        # Refresh video runs
        refreshed = await self._factory.refresh_video_run(dict(run))
        self._runs_cache[run_id] = refreshed
        await self._store.save(run_id, refreshed)
        return refreshed

    async def usage(self) -> dict[str, Any]:
        """Return usage statistics (stub)."""
        items: list[dict[str, Any]] = []
        for model in [
            {"value": "gpt-5.4", "label": "GPT-5.4", "provider": "openai"},
            {"value": "gpt-4o", "label": "GPT-4o", "provider": "openai"},
        ]:
            items.append({
                "model": str(model.get("value", "")).strip(),
                "label": str(model.get("label", model.get("value", ""))).strip(),
                "used": 0,
                "unit": "count",
                "remaining": 0,
                "remainingUnit": "count",
                "provider": str(model.get("provider", "")).strip(),
                "source": "python-default",
            })
        return {
            "items": items,
            "generatedAt": self._support.now_iso(),
            "updatedAt": self._support.now_iso(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    _runs_cache: dict[str, dict[str, Any]] = {}

    async def _create_run_by_kind_and_persist(
        self, run_id: str, kind: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        run = await self._create_run_by_kind(run_id, kind, request)
        self._runs_cache[run_id] = run
        await self._store.save(run_id, run)
        return run

    async def _create_run_by_kind(self, run_id: str, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        lower_kind = kind.lower()
        if lower_kind == GenerationRunKinds.PROBE:
            return await self._factory.create_probe_run(run_id, request)
        elif lower_kind == GenerationRunKinds.SCRIPT:
            return await self._factory.create_script_run(run_id, request)
        elif lower_kind == GenerationRunKinds.SCRIPT_ADJUST:
            return await self._factory.create_script_adjust_run(run_id, request)
        elif lower_kind == GenerationRunKinds.IMAGE:
            return await self._factory.create_image_run(run_id, request)
        elif lower_kind == GenerationRunKinds.VIDEO:
            return await self._factory.create_video_run(run_id, request)
        else:
            raise UnsupportedGenerationKindException(kind)

    @staticmethod
    def _validate_supported_kind(kind: str) -> None:
        lower_kind = kind.lower()
        supported = {
            GenerationRunKinds.PROBE,
            GenerationRunKinds.SCRIPT,
            GenerationRunKinds.SCRIPT_ADJUST,
            GenerationRunKinds.IMAGE,
            GenerationRunKinds.VIDEO,
        }
        if lower_kind not in supported:
            raise UnsupportedGenerationKindException(kind)

    def _accepted_run(self, run_id: str, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "runId": run_id,
            "kind": kind,
            "callChain": [
                self._support.call_log("generation", "run.accepted", "running", "", {"kind": kind})
            ],
            "metadata": {"async": True},
        }
        result_key = self._result_key(kind)
        return self._support.run_envelope(
            run_id, kind, request, result, result_key, GenerationRunStatuses.ACCEPTED
        )

    @staticmethod
    def _result_key(kind: str) -> str:
        lower_kind = kind.lower()
        if lower_kind == GenerationRunKinds.PROBE:
            return "resultProbe"
        if lower_kind in (GenerationRunKinds.SCRIPT, GenerationRunKinds.SCRIPT_ADJUST):
            return "resultScript"
        if lower_kind == GenerationRunKinds.IMAGE:
            return "resultImage"
        if lower_kind == GenerationRunKinds.VIDEO:
            return "resultVideo"
        return "result"

    async def _execute_async_run(
        self, run_id: str, kind: str, request: dict[str, Any]
    ) -> None:
        try:
            run = await self._create_run_by_kind(run_id, kind, request)
            self._runs_cache[run_id] = run
            await self._store.save(run_id, run)
        except Exception as ex:
            failed = self._failed_run(run_id, kind, request, ex)
            self._runs_cache[run_id] = failed
            await self._store.save(run_id, failed)

    def _failed_run(
        self, run_id: str, kind: str, request: dict[str, Any], ex: Exception
    ) -> dict[str, Any]:
        error_msg = str(ex) if str(ex) else ex.__class__.__name__
        result: dict[str, Any] = {
            "runId": run_id,
            "kind": kind,
            "error": error_msg,
            "callChain": [
                self._support.call_log("generation", "run.failed", "error", "", {
                    "error": error_msg,
                })
            ],
            "metadata": {"async": True},
        }
        result_key = self._result_key(kind)
        return self._support.run_envelope(
            run_id, kind, request, result, result_key, GenerationRunStatuses.FAILED
        )
