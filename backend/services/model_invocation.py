"""Model invocation layer - AI provider transport and strategy."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable
from urllib.parse import urlencode, urlparse

import httpx
import yaml

from backend.services.generation_service import GenerationProviderException
from backend.services.model_config_service import (
    GenerationModelKinds,
    MediaProviderProfile,
    ModelRuntimeProfile,
)
from backend.services.model_response_parsing import (
    extract_first_string,
    extract_text_response,
    extract_video_task_id,
    extract_video_task_message,
    extract_video_task_status,
    extract_video_url,
    first_non_blank,
    map_value,
    string_value,
)

logger = logging.getLogger(__name__)

# Maximum number of candidates listed in "checked candidates" description
_MAX_CHECKED_CANDIDATES_IN_MESSAGE = 12


# =============================================================================
# GenerationConfigurationException
# =============================================================================


class GenerationConfigurationException(Exception):
    """Raised when generation config is missing or invalid."""

    pass


# =============================================================================
# GenerationConfigPathLocator
# =============================================================================


@dataclass
class LocatedConfig:
    """Result of locating generation config files.

    Mirrors Java GenerationConfigPathLocator.LocatedConfig record.
    """

    config_dir: Path | None
    project_root: Path | None
    config_files: list[Path]
    source: str
    detail: str

    def config_file(self) -> Path | None:
        if not self.config_files:
            return None
        return self.config_files[0]


class GenerationConfigPathLocator:
    """Locates generation config files in the filesystem.

    Mirrors Java GenerationConfigPathLocator.
    Supports:
    - JIANDOU_CONFIG_DIR / jiandou.config.dir explicit config directory
    - spring.config.additional-location / spring.config.location env vars
    - ./config/ and cwd/ (spring-default)
    - ancestor directories (parent-default, only when no explicit config requested)
    """

    def __init__(self, config_dir: str = "./config"):
        self._config_dir = Path(config_dir)

    def locate_app_config(self) -> LocatedConfig:
        """Locate the generation config directory.

        Returns a LocatedConfig with the found config directory, project root,
        collected config files, source tag, and detail string.
        """
        checked_candidates: list[Path] = []

        explicit_config_requested = self._has_configured_value(
            "JIANDOU_CONFIG_DIR",
            "jiandou.config.dir",
            "spring.config.additional-location",
            "SPRING_CONFIG_ADDITIONAL_LOCATION",
            "spring.config.location",
            "SPRING_CONFIG_LOCATION",
        )

        explicit_dir = self._resolve_explicit_config_dir(checked_candidates)
        if explicit_dir is not None:
            return self._build_located_config(explicit_dir, "explicit-dir")

        from_spring_additional = self._resolve_from_spring_location(
            self._first_non_blank(
                os.environ.get("spring.config.additional-location", ""),
                os.environ.get("SPRING_CONFIG_ADDITIONAL_LOCATION", ""),
            ),
            "spring.config.additional-location",
            checked_candidates,
        )
        if from_spring_additional is not None:
            return self._build_located_config(from_spring_additional, "spring.config.additional-location")

        from_spring_location = self._resolve_from_spring_location(
            self._first_non_blank(
                os.environ.get("spring.config.location", ""),
                os.environ.get("SPRING_CONFIG_LOCATION", ""),
            ),
            "spring.config.location",
            checked_candidates,
        )
        if from_spring_location is not None:
            return self._build_located_config(from_spring_location, "spring.config.location")

        for candidate in self._spring_default_external_candidates():
            checked_candidates.append(candidate)
            if self._is_config_directory(candidate):
                return self._build_located_config(candidate, "spring-default")

        if not explicit_config_requested:
            for candidate in self._ancestor_external_candidates():
                checked_candidates.append(candidate)
                if self._is_config_directory(candidate):
                    return self._build_located_config(candidate, "parent-default")

        detail = self._describe_checked_candidates(checked_candidates)
        logger.warning("Generation config directory not found; %s", detail)
        return LocatedConfig(None, None, [], "missing", detail)

    def resolve_path(self, configured_path: str) -> Path | None:
        """Resolve a configured path relative to the located config directory.

        Mirrors Java resolvePath().
        """
        normalized = self._trim_to_empty(configured_path)
        if not normalized:
            return None
        if normalized.startswith("classpath:"):
            logger.warning("Classpath resource cannot be resolved as filesystem path: %s", normalized)
            return None
        path = Path(normalized)
        if path.is_absolute():
            return path.resolve()
        located = self.locate_app_config()
        if self._starts_with_config_prefix(normalized) and located.project_root is not None:
            return (located.project_root / path).resolve()
        if located.config_dir is not None:
            return (located.config_dir / path).resolve()
        return (Path.cwd() / path).resolve()

    def resolve_secrets_config_path(self) -> Path | None:
        """Resolve model secrets override file path.

        Mirrors Java resolveSecretsConfigPath().
        """
        located = self.locate_app_config()
        if located.config_dir is None:
            return None
        return (located.config_dir / "model" / "providers.secrets.yml").resolve()

    def collect_config_files(self, config_directory: Path | None) -> list[Path]:
        """Collect all YAML config files from well-known subdirectories.

        Mirrors Java collectConfigFiles().
        """
        if config_directory is None:
            return []
        normalized_dir = config_directory.resolve()
        if not normalized_dir.is_dir():
            return []
        files: list[Path] = []
        files.extend(self._collect_yaml_files(normalized_dir / "app"))
        files.extend(self._collect_yaml_files(normalized_dir / "pipeline"))
        files.extend(self._collect_yaml_files(normalized_dir / "catalog"))
        files.extend(
            self._collect_yaml_files(
                normalized_dir / "model",
                filter_func=lambda p: (
                    ".secrets." not in p.name
                    and p.parent != normalized_dir / "model" / "providers"
                ),
            )
        )
        files.extend(
            self._collect_yaml_files(
                normalized_dir / "model" / "providers",
                filter_func=lambda p: ".secrets." not in p.name,
            )
        )
        return files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_explicit_config_dir(self, checked_candidates: list[Path]) -> Path | None:
        for key in ("JIANDOU_CONFIG_DIR", "jiandou.config.dir"):
            value = os.environ.get(key, "").strip()
            if not value:
                continue
            candidate = Path(value).resolve()
            checked_candidates.append(candidate)
            if self._is_config_directory(candidate):
                return candidate
            logger.warning("Ignored config dir without split config files from %s=%s", key, value)
        return None

    def _resolve_from_spring_location(
        self,
        location: str,
        source_key: str,
        checked_candidates: list[Path],
    ) -> Path | None:
        value = self._trim_to_empty(location)
        if not value:
            return None
        for token in value.split(","):
            raw = self._strip_optional_prefix(self._trim_to_empty(token))
            if not raw or raw.startswith("classpath:"):
                continue
            cleaned = raw[5:] if raw.startswith("file:") else raw
            if "*" in cleaned:
                continue
            candidate = Path(cleaned)
            treat_as_dir = raw.endswith("/") or raw.endswith("\\") or candidate.is_dir()
            if not treat_as_dir:
                continue
            normalized = candidate.resolve()
            checked_candidates.append(normalized)
            if self._is_config_directory(normalized):
                return normalized
        logger.debug("No usable config directory found in %s", source_key)
        return None

    def _spring_default_external_candidates(self) -> list[Path]:
        cwd = Path.cwd().resolve()
        seen: list[Path] = []
        candidates = [cwd / "config", cwd]
        for p in candidates:
            r = p.resolve()
            if r not in seen:
                seen.append(r)
        return seen

    def _ancestor_external_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        current = Path.cwd().resolve().parent
        while current is not None:
            candidates.append((current / "config").resolve())
            candidates.append(current.resolve())
            parent = current.parent
            if parent == current:
                break
            current = parent
        seen: list[Path] = []
        deduped: list[Path] = []
        for p in candidates:
            if p not in seen:
                seen.append(p)
                deduped.append(p)
        return deduped

    def _is_config_directory(self, directory: Path) -> bool:
        return bool(self.collect_config_files(directory))

    def _collect_yaml_files(
        self,
        directory: Path,
        filter_func=lambda p: True,
    ) -> list[Path]:
        if not directory or not directory.is_dir():
            return []
        try:
            files: list[Path] = []
            for entry in sorted(directory.iterdir(), key=lambda e: str(e)):
                resolved = entry.resolve()
                if not resolved.is_file():
                    continue
                name = resolved.name.lower()
                if not (name.endswith(".yml") or name.endswith(".yaml")):
                    continue
                if filter_func(resolved):
                    files.append(resolved)
            return files
        except OSError as ex:
            logger.warning("Failed to list config directory: %s (%s)", directory.resolve(), ex)
            return []

    def _build_located_config(self, config_directory: Path, source_tag: str) -> LocatedConfig:
        config_dir = config_directory.resolve()
        project_root: Path | None = config_dir
        if (
            config_dir.name is not None
            and config_dir.name.lower() == "config"
            and config_dir.parent is not None
        ):
            project_root = config_dir.parent
        config_files = self.collect_config_files(config_dir)
        return LocatedConfig(
            config_dir=config_dir,
            project_root=project_root,
            config_files=list(config_files),
            source=f"dir:{config_dir}",
            detail=source_tag,
        )

    def _describe_checked_candidates(self, checked_candidates: list[Path]) -> str:
        if not checked_candidates:
            return "no candidate config files were provided"
        seen: list[Path] = []
        for p in checked_candidates:
            if p not in seen:
                seen.append(p)
        joined = ", ".join(str(p) for p in seen[:_MAX_CHECKED_CANDIDATES_IN_MESSAGE])
        if len(seen) > _MAX_CHECKED_CANDIDATES_IN_MESSAGE:
            joined += ", ..."
        return f"checked config candidates: {joined}"

    @staticmethod
    def _strip_optional_prefix(value: str) -> str:
        if value.startswith("optional:"):
            return value[len("optional:"):].strip()
        return value

    @staticmethod
    def _starts_with_config_prefix(value: str) -> bool:
        normalized = value.replace("\\", "/")
        return normalized.startswith("config/")

    @staticmethod
    def _trim_to_empty(value: str | None) -> str:
        return "" if value is None else value.strip()

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        for v in values:
            if v and v.strip():
                return v.strip()
        return ""

    @staticmethod
    def _has_configured_value(*keys: str) -> bool:
        return any(bool(os.environ.get(k, "").strip()) for k in keys)


# =============================================================================
# PromptTemplateResolver
# =============================================================================


class PromptTemplateResolver:
    """Resolves prompt templates from YAML files with variable substitution.

    Mirrors Java PromptTemplateResolver.
    """

    def __init__(
        self,
        config_path_locator: GenerationConfigPathLocator | None = None,
        fail_fast_on_prompt_error: bool | None = None,
    ):
        self._config_path_locator = config_path_locator or GenerationConfigPathLocator()
        self._errors: list[str] = []
        if fail_fast_on_prompt_error is not None:
            self._fail_fast = fail_fast_on_prompt_error
        else:
            self._fail_fast = self._resolve_prompt_fail_fast()

    def system_prompt(self, prompt_name: str, key: str) -> str:
        """Resolve a system prompt template by name and key."""
        prompt_file = self._locate_prompt_file(prompt_name)
        if prompt_file is None or not prompt_file.exists():
            return self._fail_or_empty(
                f"Prompt file not found for promptName={prompt_name} key={key}",
                None,
            )
        try:
            resolved = self._load_yaml_prompt(prompt_file, key)
            self._errors = []
            return resolved
        except (ValueError, KeyError, yaml.YAMLError) as ex:
            return self._fail_or_empty(
                f"Failed to load prompt template from file={prompt_file.resolve()} key={key}: {ex}",
                ex,
            )

    def prompt_errors(self) -> list[str]:
        """Return list of current prompt resolution errors."""
        return list(self._errors)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _locate_prompt_file(self, prompt_name: str) -> Path | None:
        prompt_directory = self._first_non_blank(
            os.environ.get("JIANDOU_PROMPT_DIR", ""),
            os.environ.get("jiandou.prompt.dir", ""),
            "prompts",
        )
        base = self._config_path_locator.resolve_path(prompt_directory)
        if base is None:
            self._fail_or_empty(f"Prompt directory cannot be resolved: {prompt_directory}", None)
            return None
        yml_path = (base / f"{prompt_name}.yml").resolve()
        if yml_path.exists():
            return yml_path
        yaml_path = (base / f"{prompt_name}.yaml").resolve()
        if yaml_path.exists():
            return yaml_path
        return None

    def _load_yaml_prompt(self, prompt_file: Path, key: str) -> str:
        with open(prompt_file) as f:
            loaded = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            raise ValueError("Prompt yaml is empty")
        normalized = self._normalize_map(loaded)
        system_prompts = normalized.get("system_prompts")
        if not isinstance(system_prompts, dict):
            raise ValueError("Prompt yaml missing system_prompts section")
        value = self._normalize_map(system_prompts).get(key)
        if value is None:
            raise KeyError(f"Prompt key not found: {key}")
        text = str(value).strip()
        if not text:
            raise ValueError(f"Prompt key is blank: {key}")
        return text

    def _fail_or_empty(self, message: str, cause: Exception | None) -> str:
        self._errors = [message]
        if cause is None:
            logger.warning(message)
        else:
            logger.error(message, exc_info=cause)
        if self._fail_fast:
            raise GenerationConfigurationException(message)
        return ""

    def _resolve_prompt_fail_fast(self) -> bool:
        prompt_level = self._first_non_blank(
            os.environ.get("JIANDOU_PROMPT_FAIL_FAST", ""),
            os.environ.get("jiandou.prompt.fail-fast", ""),
        )
        if prompt_level:
            return self._bool_value(prompt_level)
        return self._bool_value(
            self._first_non_blank(
                os.environ.get("JIANDOU_CONFIG_FAIL_FAST", ""),
                "false",
            )
        )

    @staticmethod
    def _bool_value(raw: str) -> bool:
        n = (raw or "").strip().lower()
        return n in ("1", "true", "yes", "on")

    @staticmethod
    def _normalize_map(source: dict) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in source.items():
            if isinstance(value, dict):
                result[str(key)] = PromptTemplateResolver._normalize_map(value)
            else:
                result[str(key)] = value
        return result

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        for v in values:
            if v and v.strip():
                return v.strip()
        return ""


# =============================================================================
# DTOs for text model invocation
# =============================================================================


@dataclass
class TextModelInvocation:
    """Parameters for invoking a text model.

    Mirrors Java TextModelInvocation.
    """

    system_prompt: str = ""
    user_prompt: str = ""
    temperature: float = 0.0
    max_tokens: int = 0


@dataclass
class TextModelResponse:
    """Response from a text model provider.

    Mirrors Java TextModelResponse.
    """

    text: str = ""
    endpoint: str = ""
    endpoint_host: str = ""
    latency_ms: int = 0
    responses_api: bool = False
    response_id: str = ""
    provider_request: dict[str, Any] = field(default_factory=dict)
    provider_response: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@dataclass
class PreparedTextModelRequest:
    """Prepared request payload for a text model.

    Mirrors Java PreparedTextModelRequest.
    """

    endpoint: str = ""
    body: dict[str, Any] = field(default_factory=dict)
    responses_api: bool = False


class TextModelTransportPolicy:
    """Utility for building text model transport endpoints.

    Mirrors Java TextModelTransportPolicy.
    """

    @staticmethod
    def resolve_endpoint(base_url: str, use_responses_api: bool) -> str:
        """Resolve the full API endpoint from the base URL.

        Appends /chat/completions or /responses path.
        """
        normalized = base_url.rstrip("/")
        if normalized.endswith("/responses"):
            normalized = normalized[: -len("/responses")]
        if normalized.endswith("/chat/completions"):
            normalized = normalized[: -len("/chat/completions")]
        if use_responses_api:
            return normalized + "/responses"
        return normalized + "/chat/completions"

    @staticmethod
    def supports_responses_api(profile: ModelRuntimeProfile) -> bool:
        """Check whether the profile supports the Responses API.

        Mirrors Java TextModelTransportPolicy.supportsResponsesApi.
        """
        if hasattr(profile, "supports_responses_api"):
            return profile.supports_responses_api()
        return False


@runtime_checkable
class TextModelInvocationStrategy(Protocol):
    """Strategy interface for preparing text model requests.

    Mirrors Java TextModelInvocationStrategy.
    """

    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool:
        """Return True if this strategy applies to the given profile/invocation."""
        ...

    def prepare(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> PreparedTextModelRequest:
        """Build a prepared request for the given profile and invocation."""
        ...


class ChatCompletionsInvocationStrategy:
    """Fallback strategy for OpenAI-compatible chat completions API.

    Mirrors Java ChatCompletionsInvocationStrategy.
    """

    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool:
        return True

    def prepare(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> PreparedTextModelRequest:
        body: dict[str, Any] = {
            "model": profile.config.provider_model,
            "messages": [
                {"role": "system", "content": invocation.system_prompt},
                {"role": "user", "content": invocation.user_prompt},
            ],
            "temperature": invocation.temperature,
            "max_tokens": invocation.max_tokens,
        }
        return PreparedTextModelRequest(
            endpoint=TextModelTransportPolicy.resolve_endpoint(profile.base_url, False),
            body=body,
            responses_api=False,
        )


class ResponsesApiInvocationStrategy:
    """Strategy for models supporting the OpenAI Responses API.

    Mirrors Java ResponsesApiInvocationStrategy.
    """

    def supports(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> bool:
        return TextModelTransportPolicy.supports_responses_api(profile)

    def prepare(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> PreparedTextModelRequest:
        body: dict[str, Any] = {
            "model": profile.config.provider_model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": invocation.system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": invocation.user_prompt}],
                },
            ],
            "temperature": invocation.temperature,
            "max_output_tokens": invocation.max_tokens,
        }
        return PreparedTextModelRequest(
            endpoint=TextModelTransportPolicy.resolve_endpoint(profile.base_url, True),
            body=body,
            responses_api=True,
        )


@runtime_checkable
class TextModelProvider(Protocol):
    """Provider interface for text models.

    Mirrors Java TextModelProvider.
    """

    def supports(self, profile: ModelRuntimeProfile) -> bool:
        ...

    def generate(self, profile: ModelRuntimeProfile, invocation: TextModelInvocation) -> TextModelResponse:
        ...


# =============================================================================
# TextProviderTransport
# =============================================================================


class TextProviderTransport:
    """HTTP transport for text model providers.

    Mirrors Java TextProviderTransport.
    """

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0), trust_env=False)

    async def send_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        error_prefix: str,
    ) -> httpx.Response:
        """Send a JSON POST request to the text model endpoint."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        timeout = max(30, timeout_seconds)
        raw_body = self._encode(body)
        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                content=raw_body,
                timeout=timeout,
            )
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request={"method": "POST", "url": endpoint, "body": body},
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: http {response.status_code} {self._truncate(response.text, 320)}",
                provider_request={"method": "POST", "url": endpoint, "body": body},
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    async def send(self, request: httpx.Request, error_prefix: str) -> httpx.Response:
        """Send a pre-built HTTP request."""
        request_payload: dict[str, Any] = {"method": request.method, "url": str(request.url)}
        return await self._send_raw(request, error_prefix, request_payload)

    async def _send_raw(
        self,
        request: httpx.Request,
        error_prefix: str,
        request_payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request=request_payload,
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: http {response.status_code} {self._truncate(response.text, 320)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    def decode(self, raw: str) -> dict[str, Any]:
        """Decode a JSON response body."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as ex:
            raise GenerationProviderException(f"text model response decode failed: {ex}")

    def extract_text(self, response_map: dict[str, Any]) -> str:
        """Extract text content from a text model response, trying multiple formats.

        Supports: output_text, output (object), output (array), choices, message, text.
        """
        return extract_text_response(response_map)

    def endpoint_host(self, endpoint: str) -> str:
        """Extract the host from an endpoint URL."""
        try:
            host = urlparse(endpoint).hostname
            return host or ""
        except Exception:
            return ""

    def string_value(self, value: object) -> str:
        return string_value(value)

    def _encode(self, body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as ex:
            raise GenerationProviderException(f"text model request encode failed: {ex}")

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]


# =============================================================================
# OpenAiCompatibleTextModelProvider
# =============================================================================


class OpenAiCompatibleTextModelProvider:
    """OpenAI-compatible text model provider.

    Mirrors Java OpenAiCompatibleTextModelProvider.
    Uses the strategy pattern to select between chat completions and responses API.
    """

    def __init__(
        self,
        transport: TextProviderTransport | None = None,
        invocation_strategies: list[TextModelInvocationStrategy] | None = None,
    ):
        self._transport = transport or TextProviderTransport()
        self._invocation_strategies = list(
            invocation_strategies
            if invocation_strategies is not None
            else [ResponsesApiInvocationStrategy(), ChatCompletionsInvocationStrategy()]
        )

    def supports(self, profile: ModelRuntimeProfile) -> bool:
        return profile is not None and bool(profile.config.provider)

    async def generate(
        self,
        profile: ModelRuntimeProfile,
        invocation: TextModelInvocation,
    ) -> TextModelResponse:
        if not profile.ready:
            raise GenerationConfigurationException("text model config missing api key or base url")
        prepared = self._prepare(profile, invocation)
        import time
        started_at = time.monotonic_ns()
        response = await self._transport.send_json(
            prepared.endpoint,
            profile.api_key,
            prepared.body,
            profile.config.timeout_seconds,
            "text model request failed",
        )
        latency_ms = int((time.monotonic_ns() - started_at) / 1_000_000)
        response_map = self._transport.decode(response.text)
        provider_request: dict[str, Any] = {
            "method": "POST",
            "endpoint": prepared.endpoint,
            "body": prepared.body,
        }
        text = self._transport.extract_text(response_map).strip()
        if not text:
            raise GenerationProviderException(
                "text model response is empty",
                provider_request=provider_request,
                provider_response=response_map,
                http_status=response.status_code,
            )
        return TextModelResponse(
            text=text,
            endpoint=prepared.endpoint,
            endpoint_host=self._transport.endpoint_host(prepared.endpoint),
            latency_ms=latency_ms,
            responses_api=prepared.responses_api,
            response_id=self._transport.string_value(response_map.get("id")),
            provider_request=provider_request,
            provider_response=response_map,
            http_status=response.status_code,
        )

    def _prepare(
        self,
        profile: ModelRuntimeProfile,
        invocation: TextModelInvocation,
    ) -> PreparedTextModelRequest:
        tried_strategies: list[str] = []
        for strategy in self._invocation_strategies:
            tried_strategies.append(strategy.__class__.__name__)
            if strategy.supports(profile, invocation):
                return strategy.prepare(profile, invocation)
        raise GenerationProviderException(
            "no text model invocation strategy matched: " + ", ".join(tried_strategies)
        )


# =============================================================================
# DTOs for image model invocation
# =============================================================================


@dataclass
class ImageGenerationRequest:
    """Parameters for invoking an image generation model.

    Mirrors Java ImageGenerationRequest.
    """

    requested_model: str = ""
    prompt: str = ""
    width: int = 1024
    height: int = 1024
    reference_image_urls: list[str] = field(default_factory=list)
    reference_image_url: str = ""
    seed: int | None = None


@dataclass
class RemoteImageGenerationResult:
    """Result from an image generation provider.

    Mirrors Java RemoteImageGenerationResult.
    """

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
    """Provider interface for image models.

    Mirrors Java ImageModelProvider.
    """

    def supports(self, profile: MediaProviderProfile) -> bool:
        ...

    def generate(self, profile: MediaProviderProfile, request: ImageGenerationRequest) -> RemoteImageGenerationResult:
        ...


# =============================================================================
# ImageProviderTransport
# =============================================================================


@dataclass
class DownloadedBinary:
    """Downloaded binary data with MIME type.

    Mirrors Java ImageProviderTransport.DownloadedBinary record.
    """
    data: bytes = b""
    mime_type: str = ""


@dataclass
class MultipartFilePart:
    """File part for multipart uploads.

    Mirrors Java ImageProviderTransport.MultipartFilePart record.
    """
    field_name: str = ""
    file_name: str = ""
    content_type: str = "application/octet-stream"
    data: bytes = b""


class ImageProviderTransport:
    """HTTP transport for image generation providers.

    Mirrors Java ImageProviderTransport.
    Supports JSON POST, multipart upload, and binary download operations.
    """

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            trust_env=False,
        )

    async def send_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a JSON POST request to the image provider.

        Retries transient server errors (500+) and network errors up to 3 times
        with exponential backoff, matching the retry behaviour of
        :meth:`download_binary`."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        timeout = max(30, timeout_seconds)
        raw_body = self._encode(body)
        request_payload: dict[str, Any] = {"method": "POST", "url": endpoint, "body": body}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    endpoint,
                    headers=headers,
                    content=raw_body,
                    timeout=timeout,
                )
            except httpx.RequestError as ex:
                last_error = ex
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
            if response.status_code < 200 or response.status_code >= 300:
                # Retry transient server errors (500, 502, 503, 504)
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise GenerationProviderException(
                    f"provider request failed: {ImageProviderTransport._error_summary(response.status_code, response.text)}",
                    provider_request=request_payload,
                    provider_response=response.text,
                    http_status=response.status_code,
                )
            return response
        # All retries exhausted – surface the last error
        if last_error is not None:
            message = str(last_error) or last_error.__class__.__name__
            raise GenerationProviderException(
                f"provider request failed: {message}",
                provider_request=request_payload,
                http_status=0,
            )
        # Should not reach here, but satisfy the type checker
        raise GenerationProviderException(
            "provider request failed: all retries exhausted",
            provider_request=request_payload,
        )

    async def download_binary(self, url: str, timeout_seconds: int) -> DownloadedBinary:
        """Download binary data from a URL (e.g., generated image).

        Retries transient network errors up to 3 times with exponential backoff."""
        headers = {
            "User-Agent": "jiandou-python/0.1",
            "Accept": "*/*",
        }
        timeout = max(15, timeout_seconds)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.get(url, headers=headers, timeout=timeout)
            except httpx.RequestError as ex:
                last_error = ex
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s
                continue
            if response.status_code < 200 or response.status_code >= 300:
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise GenerationProviderException(
                    f"remote media download failed: http {response.status_code}"
                )
            mime_type = response.headers.get("content-type", "")
            return DownloadedBinary(data=response.content, mime_type=mime_type or "")
        raise GenerationProviderException(f"remote media download failed: {last_error}")

    async def send_multipart(
        self,
        endpoint: str,
        api_key: str,
        fields: dict[str, str],
        files: list[MultipartFilePart],
        timeout_seconds: int,
        request_payload: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a multipart/form-data POST request."""
        boundary = f"jiandou-{uuid.uuid4().hex}"
        body_bytes = self._multipart_body(boundary, fields, files)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        }
        timeout = max(30, timeout_seconds)
        payload = request_payload if request_payload is not None else {"method": "POST", "url": endpoint}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    endpoint,
                    headers=headers,
                    content=body_bytes,
                    timeout=timeout,
                )
            except httpx.RequestError as ex:
                last_error = ex
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
            if response.status_code < 200 or response.status_code >= 300:
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise GenerationProviderException(
                    f"provider multipart request failed: http {response.status_code} {self._truncate(response.text, 320)}",
                    provider_request=payload,
                    provider_response=response.text,
                    http_status=response.status_code,
                )
            return response
        if last_error is not None:
            raise GenerationProviderException(
                f"provider multipart request failed: {last_error}",
                provider_request=payload,
                http_status=0,
            )
        raise GenerationProviderException(
            "provider multipart request failed: all retries exhausted",
            provider_request=payload,
        )

    async def send(self, request: httpx.Request, error_prefix: str) -> httpx.Response:
        """Send a pre-built HTTP request."""
        request_payload: dict[str, Any] = {"method": request.method, "url": str(request.url)}
        return await self._send_raw(request, error_prefix, request_payload)

    async def _send_raw(
        self,
        request: httpx.Request,
        error_prefix: str,
        request_payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request=request_payload,
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: {ImageProviderTransport._error_summary(response.status_code, response.text)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    def decode(self, raw: str) -> dict[str, Any]:
        """Decode a JSON response body."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as ex:
            raise GenerationProviderException(f"provider response decode failed: {ex}")

    def extract_first_string(self, raw: object, *keys: str) -> str:
        """Recursively search for the first non-blank string value matching any key.

        Mirrors Java ImageProviderTransport.extractFirstString.
        """
        return extract_first_string(raw, *keys)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _encode(self, body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as ex:
            raise GenerationProviderException(f"provider request encode failed: {ex}")

    @staticmethod
    def _multipart_body(
        boundary: str,
        fields: dict[str, str],
        files: list[MultipartFilePart],
    ) -> bytes:
        parts: list[bytes] = []
        line_break = "\r\n"
        for name, value in fields.items():
            parts.append(
                f"--{boundary}{line_break}"
                f'Content-Disposition: form-data; name="{name}"{line_break}'
                f"{line_break}"
                f"{value}{line_break}".encode()
            )
        for file_part in files:
            parts.append(
                f"--{boundary}{line_break}"
                f'Content-Disposition: form-data; name="{file_part.field_name}"; filename="{file_part.file_name}"{line_break}'
                f"Content-Type: {file_part.content_type or 'application/octet-stream'}{line_break}"
                f"{line_break}".encode()
            )
            parts.append(file_part.data if file_part.data is not None else b"")
            parts.append(line_break.encode("utf-8"))
        parts.append(f"--{boundary}--{line_break}".encode())
        return b"".join(parts)

    @staticmethod
    def _error_summary(status_code: int, body: str | None) -> str:
        """Format error message with explicit tags for known non-retryable statuses."""
        normalized_body = (body or "").strip()
        status_tags: dict[int, str] = {
            429: "rate limit / quota exceeded",
            402: "payment required / quota exceeded",
            403: "forbidden / permission denied",
            401: "unauthorized / authentication failed",
        }
        tag = status_tags.get(status_code)
        truncated = ImageProviderTransport._truncate(normalized_body, 320) if normalized_body else ""
        if tag:
            return f"http {status_code} {tag}" + (f": {truncated}" if truncated else "")
        return f"http {status_code}" + (f" {truncated}" if truncated else "")

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]


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
        provider_model = self._blank_to(profile.config.provider_model, request.requested_model)
        size = f"{request.width}x{request.height}"
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
        provider_model = self._blank_to(profile.config.provider_model, request.requested_model)
        size = f"{request.width}x{request.height}"
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
        # OpenAI images/generations response: {"data": [{"url": "...", "b64_json": "..."}]}
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
            except (ValueError, base64.binascii.Error) as ex:
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
            requested_size=f"{request.width}x{request.height}",
            provider_request=provider_request,
            provider_response=payload,
            http_status=http_status,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
    def _blank_to(primary: str, fallback: str) -> str:
        return fallback if not primary else primary


# =============================================================================
# DTOs for video model invocation
# =============================================================================


@dataclass
class VideoGenerationRequest:
    """Parameters for invoking a video generation model.

    Mirrors Java VideoGenerationRequest.
    """

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
    """Result of submitting a video generation task.

    Mirrors Java RemoteVideoTaskSubmission.
    """

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
    """Result of querying a video task status.

    Mirrors Java RemoteTaskQueryResult.
    """

    task_id: str = ""
    task_status: str = "UNKNOWN"
    video_url: str = ""
    task_message: str = ""
    provider_response: dict[str, Any] = field(default_factory=dict)
    provider_request: dict[str, Any] = field(default_factory=dict)
    http_status: int = 0


@runtime_checkable
class VideoModelProvider(Protocol):
    """Provider interface for video models.

    Mirrors Java VideoModelProvider.
    """

    def supports(self, profile: MediaProviderProfile) -> bool:
        ...

    async def submit(self, profile: MediaProviderProfile, request: VideoGenerationRequest) -> RemoteVideoTaskSubmission:
        ...

    async def query(self, profile: MediaProviderProfile, remote_task_id: str) -> RemoteTaskQueryResult:
        ...


# =============================================================================
# VideoProviderTransport
# =============================================================================


class VideoProviderTransport:
    """HTTP transport for video generation providers.

    Mirrors Java VideoProviderTransport.
    Supports JSON POST, GET query, and response parsing for task-based APIs.
    """

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            trust_env=False,
        )

    async def send_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a JSON POST request to the video provider."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        timeout = max(30, timeout_seconds)
        raw_body = self._encode(body)
        request_payload: dict[str, Any] = {"method": "POST", "url": endpoint, "body": body}
        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                content=raw_body,
                timeout=timeout,
            )
        except httpx.RequestError as ex:
            message = str(ex) or ex.__class__.__name__
            raise GenerationProviderException(
                f"provider request failed: {message}",
                provider_request=request_payload,
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"provider request failed: {self._summarize_error_response(response.status_code, response.text)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    async def send(self, request: httpx.Request, error_prefix: str) -> httpx.Response:
        """Send a pre-built HTTP request."""
        request_payload: dict[str, Any] = {"method": request.method, "url": str(request.url)}
        return await self._send_raw(request, error_prefix, request_payload)

    async def _send_raw(
        self,
        request: httpx.Request,
        error_prefix: str,
        request_payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request=request_payload,
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: {self._summarize_error_response(response.status_code, response.text)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    def decode(self, raw: str) -> dict[str, Any]:
        """Decode a JSON response body."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as ex:
            raise GenerationProviderException(f"provider response decode failed: {ex}")

    def extract_task_id(self, payload: dict[str, Any]) -> str:
        """Extract task ID from response payload, trying multiple key formats."""
        return extract_video_task_id(payload)

    def extract_video_url(self, payload: dict[str, Any]) -> str:
        """Extract video URL from response payload."""
        return extract_video_url(payload)

    def extract_task_status(self, payload: dict[str, Any]) -> str:
        """Extract task status from response payload."""
        return extract_video_task_status(payload)

    def extract_task_message(self, payload: dict[str, Any]) -> str:
        """Extract task message/error from response payload."""
        return extract_video_task_message(payload)

    def encode_path_segment(self, value: str) -> str:
        """URL-encode a path segment.

        Mirrors Java VideoProviderTransport.encodePathSegment.
        """
        from urllib.parse import quote
        return quote(value, safe="")

    def extract_first_string(self, raw: object, *keys: str) -> str:
        """Recursively search for the first non-blank string value matching any key.

        Mirrors Java VideoProviderTransport.extractFirstString.
        """
        return extract_first_string(raw, *keys)

    def map_value(self, value: object) -> dict[str, Any]:
        """Convert a value to a normalized dict, or return empty dict.

        Mirrors Java VideoProviderTransport.mapValue.
        """
        return map_value(value)

    def _encode(self, body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as ex:
            raise GenerationProviderException(f"provider request encode failed: {ex}")

    @staticmethod
    def _last_resort_body_string(request_payload: dict[str, Any] | None) -> str:
        body = (request_payload or {}).get("body")
        if isinstance(body, str):
            return body
        if isinstance(body, dict):
            return str(body)
        return str(body) if body else ""

    @staticmethod
    def _string_value(value: object) -> str:
        return string_value(value)

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        return first_non_blank(*values)

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]

    @staticmethod
    def _looks_like_html(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return (
            normalized.startswith("<!doctype html")
            or normalized.startswith("<html")
            or "<title>" in normalized
            or "<body" in normalized
        )

    @staticmethod
    def _summarize_error_response(status_code: int, body: str | None) -> str:
        normalized_body = (body or "").strip()
        # Explicit HTTP status tags for known non-retryable conditions so
        # permanent-error detection (is_permanent_provider_error) can identify them.
        _STATUS_TAGS: dict[int, str] = {
            429: "rate limit / quota exceeded",
            402: "payment required / quota exceeded",
            403: "forbidden / permission denied",
            401: "unauthorized / authentication failed",
        }
        status_tag = _STATUS_TAGS.get(status_code)
        if not normalized_body:
            prefix = f"http {status_code}" + (f" {status_tag}" if status_tag else "")
            return prefix
        if VideoProviderTransport._looks_like_html(normalized_body):
            html_summaries = {
                502: "http 502 upstream gateway error",
                503: "http 503 upstream service unavailable",
                504: "http 504 upstream gateway timeout",
            }
            return html_summaries.get(status_code, f"http {status_code} upstream html error page")
        truncated = VideoProviderTransport._truncate(normalized_body, 320)
        if status_tag:
            return f"http {status_code} {status_tag}: {truncated}"
        return f"http {status_code} {truncated}"


# =============================================================================
# SeedanceVideoModelProvider
# =============================================================================


class SeedanceVideoModelProvider:
    """Seedance video generation provider.

    Mirrors Java SeedanceVideoModelProvider.
    Supports task submission and status querying via async HTTP.
    """

    def __init__(self, transport: VideoProviderTransport | None = None):
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
        provider_model = self._blank_to(profile.config.provider_model, request.requested_model)
        body = self._build_seedance_video_request_body(
            provider_model,
            request.prompt,
            request.width,
            request.height,
            request.duration_seconds,
            request.first_frame_url,
            request.last_frame_url,
            request.seed,
            request.camera_fixed,
            request.watermark,
            request.return_last_frame,
            request.generate_audio,
        )
        submit_response = await self._transport.send_json(
            profile.base_url,
            profile.api_key,
            body,
            profile.config.timeout_seconds,
            {"X-Api-Key": profile.api_key},
        )
        submit_payload = self._transport.decode(submit_response.text)
        task_id = self._transport.extract_task_id(submit_payload)
        if not task_id:
            raise GenerationProviderException(
                "seedance task response missing task id",
                provider_request={"method": "POST", "endpoint": profile.base_url, "body": body},
                provider_response=submit_payload,
                http_status=submit_response.status_code,
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
            provider_response=submit_payload,
            http_status=submit_response.status_code,
        )

    async def query(
        self,
        profile: MediaProviderProfile,
        remote_task_id: str,
    ) -> RemoteTaskQueryResult:
        normalized_task_id = (remote_task_id or "").strip()
        if not normalized_task_id:
            raise GenerationProviderException("seedance task id is required")
        if not profile.ready or not profile.task_base_url or not profile.task_base_url.strip():
            raise GenerationConfigurationException("seedance config missing task endpoint or api key")
        poll_url = profile.task_base_url.rstrip("/") + "/" + self._transport.encode_path_segment(normalized_task_id)
        import httpx as _httpx
        request = _httpx.Request(
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
        request_payload: dict[str, Any] = {"method": "GET", "url": poll_url}
        return RemoteTaskQueryResult(
            task_id=self._blank_to(self._transport.extract_task_id(payload), normalized_task_id),
            task_status=self._transport.extract_task_status(payload),
            video_url=self._transport.extract_video_url(payload),
            task_message=self._transport.extract_task_message(payload),
            provider_response=payload,
            provider_request=request_payload,
            http_status=response.status_code,
        )

    def _build_seedance_video_request_body(
        self,
        provider_model: str,
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
        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "role": "first_frame",
                "image_url": {"url": first_frame_url},
            },
        ]
        if last_frame_url and last_frame_url.strip():
            content.append({
                "type": "image_url",
                "role": "last_frame",
                "image_url": {"url": last_frame_url},
            })
        body: dict[str, Any] = {
            "model": provider_model,
            "content": content,
            "ratio": self._aspect_ratio(width, height),
            "resolution": self._seedance_resolution(width, height),
            "duration": duration_seconds,
            "camera_fixed": camera_fixed,
            "watermark": watermark,
            "return_last_frame": return_last_frame,
            "generate_audio": generate_audio,
        }
        if seed is not None:
            body["seed"] = seed
        return body

    @staticmethod
    def _aspect_ratio(width: int, height: int) -> str:
        if width == height:
            return "1:1"
        return "16:9" if width > height else "9:16"

    @staticmethod
    def _seedance_resolution(width: int, height: int) -> str:
        longest_edge = max(width, height)
        if longest_edge >= 1920:
            return "1080p"
        if longest_edge >= 1280:
            return "720p"
        return "480p"

    @staticmethod
    def _blank_to(primary: str, fallback: str) -> str:
        return fallback if not primary else primary


# =============================================================================
# AgnesVideoModelProvider
# =============================================================================


class AgnesVideoModelProvider:
    """Agnes Video V2.0 generation provider.

    Submits video generation tasks to the Agnes AI API and polls for results.
    API docs: https://agnes-ai.com/doc/agnes-video-v20
    """

    def __init__(self, transport: VideoProviderTransport | None = None):
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
        provider_model = self._blank_to(profile.config.provider_model, request.requested_model)
        frame_rate = 24
        body = self._build_agnes_video_request_body(
            provider_model,
            request.prompt,
            request.width,
            request.height,
            request.duration_seconds,
            frame_rate,
            request.first_frame_url,
            request.last_frame_url,
            request.seed,
        )
        submit_response = await self._transport.send_json(
            profile.base_url,
            profile.api_key,
            body,
            profile.config.timeout_seconds,
            {"Authorization": f"Bearer {profile.api_key}"},
        )
        submit_payload = self._transport.decode(submit_response.text)
        task_id = self._transport.extract_task_id(submit_payload)
        if not task_id:
            raise GenerationProviderException(
                "agnes task response missing task id",
                provider_request={"method": "POST", "endpoint": profile.base_url, "body": body},
                provider_response=submit_payload,
                http_status=submit_response.status_code,
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
            provider_response=submit_payload,
            http_status=submit_response.status_code,
        )

    async def query(
        self,
        profile: MediaProviderProfile,
        remote_task_id: str,
    ) -> RemoteTaskQueryResult:
        normalized_task_id = (remote_task_id or "").strip()
        if not normalized_task_id:
            raise GenerationProviderException("agnes task id is required")
        if not profile.ready:
            raise GenerationConfigurationException("agnes config missing task endpoint or api key")
        poll_base = (profile.task_base_url or profile.base_url).rstrip("/")
        poll_url = f"{poll_base}/{normalized_task_id}"
        import httpx as _httpx
        request = _httpx.Request(
            "GET",
            poll_url,
            headers={
                "Authorization": f"Bearer {profile.api_key}",
                "Accept": "application/json",
            },
        )
        response = await self._transport.send(request, "agnes task query failed")
        payload = self._transport.decode(response.text)
        request_payload: dict[str, Any] = {"method": "GET", "url": poll_url}
        return RemoteTaskQueryResult(
            task_id=self._blank_to(self._transport.extract_task_id(payload), normalized_task_id),
            task_status=self._transport.extract_task_status(payload),
            video_url=self._transport.extract_video_url(payload),
            task_message=self._transport.extract_task_message(payload),
            provider_response=payload,
            provider_request=request_payload,
            http_status=response.status_code,
        )

    def _build_agnes_video_request_body(
        self,
        provider_model: str,
        prompt: str,
        width: int,
        height: int,
        duration_seconds: int,
        frame_rate: int,
        first_frame_url: str,
        last_frame_url: str,
        seed: int | None,
    ) -> dict[str, Any]:
        num_frames = self._compute_num_frames(duration_seconds, frame_rate)
        body: dict[str, Any] = {
            "model": provider_model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
        }
        first = first_frame_url.strip() if first_frame_url else ""
        last = last_frame_url.strip() if last_frame_url else ""
        if first and last:
            body["mode"] = "keyframes"
            body["image"] = first
            body["extra_body"] = {
                "image": [first, last],
                "mode": "keyframes",
            }
        elif first:
            body["image"] = first
        if seed is not None:
            body["seed"] = seed
        return body

    @staticmethod
    def _compute_num_frames(duration_seconds: int, frame_rate: int = 24) -> int:
        """Map duration_seconds to a valid Agnes num_frames (8n+1, ≤ 441)."""
        target = duration_seconds * frame_rate
        best = 81
        for n in range(10, 56):
            candidate = 8 * n + 1
            if abs(candidate - target) < abs(best - target):
                best = candidate
        return min(best, 441)

    @staticmethod
    def _blank_to(primary: str, fallback: str) -> str:
        return fallback if not primary else primary


# =============================================================================
# CompositeVideoModelProvider
# =============================================================================


class CompositeVideoModelProvider:
    """Multiplexing video provider that delegates to the right sub-provider
    based on profile.config.provider.
    """

    def __init__(self, providers: list[VideoModelProvider] | None = None):
        self._providers: list[VideoModelProvider] = providers or []

    def supports(self, profile: MediaProviderProfile) -> bool:
        return any(p.supports(profile) for p in self._providers)

    async def submit(
        self,
        profile: MediaProviderProfile,
        request: VideoGenerationRequest,
    ) -> RemoteVideoTaskSubmission:
        provider = self._resolve(profile)
        return await provider.submit(profile, request)

    async def query(
        self,
        profile: MediaProviderProfile,
        remote_task_id: str,
    ) -> RemoteTaskQueryResult:
        provider = self._resolve(profile)
        return await provider.query(profile, remote_task_id)

    def _resolve(self, profile: MediaProviderProfile) -> VideoModelProvider:
        for p in self._providers:
            if p.supports(profile):
                return p
        raise GenerationProviderException(
            f"no video provider supports provider={profile.config.provider}"
        )
