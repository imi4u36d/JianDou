from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape as html_escape
from math import gcd
from pathlib import Path
from typing import Any, Iterable, Literal
import base64
import json
import mimetypes
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel, Field, model_validator

from ai_cut_ai.generation import ImageGenerationModule, VideoGenerationModule
from ai_cut_shared.config import Settings, resolve_text_analysis_target
from ai_cut_storage.storage import MediaStorage
from ai_cut_shared.utils import (
    build_text_request_body,
    extract_llm_text_response,
    looks_like_qwen_model,
    new_id,
    parse_json_bytes,
    parse_json_object,
    resolve_llm_request_endpoint,
    should_use_responses_api,
    truncate_text,
)

_SchemaGenerationVersionInfo = None
_SchemaGenerationOptionsResponse = None
_SchemaGenerationTextAnalysisModelInfo = None
_SchemaGenerationVideoModelOption = None
_SchemaGenerationVideoSizeOption = None
_SchemaGenerateTextMediaRequest = None
_SchemaGenerateTextMediaResponse = None
_SchemaProbeTextAnalysisModelRequest = None
_SchemaProbeTextAnalysisModelResponse = None
_SchemaGenerateTextScriptRequest = None
_SchemaGenerateTextScriptResponse = None

try:
    from ai_cut_shared.schemas import GenerationVersionInfo as _SchemaGenerationVersionInfo  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVersionInfo = None

try:
    from ai_cut_shared.schemas import GenerationOptionsResponse as _SchemaGenerationOptionsResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationOptionsResponse = None

try:
    from ai_cut_shared.schemas import GenerationTextAnalysisModelInfo as _SchemaGenerationTextAnalysisModelInfo  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationTextAnalysisModelInfo = None

try:
    from ai_cut_shared.schemas import GenerationVideoModelOption as _SchemaGenerationVideoModelOption  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVideoModelOption = None

try:
    from ai_cut_shared.schemas import GenerationVideoSizeOption as _SchemaGenerationVideoSizeOption  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVideoSizeOption = None

try:
    from ai_cut_shared.schemas import GenerateTextMediaRequest as _SchemaGenerateTextMediaRequest  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextMediaRequest = None

try:
    from ai_cut_shared.schemas import GenerateTextMediaResponse as _SchemaGenerateTextMediaResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextMediaResponse = None

try:
    from ai_cut_shared.schemas import ProbeTextAnalysisModelRequest as _SchemaProbeTextAnalysisModelRequest  # type: ignore[attr-defined]
except Exception:
    _SchemaProbeTextAnalysisModelRequest = None

try:
    from ai_cut_shared.schemas import ProbeTextAnalysisModelResponse as _SchemaProbeTextAnalysisModelResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaProbeTextAnalysisModelResponse = None

try:
    from ai_cut_shared.schemas import GenerateTextScriptRequest as _SchemaGenerateTextScriptRequest  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextScriptRequest = None

try:
    from ai_cut_shared.schemas import GenerateTextScriptResponse as _SchemaGenerateTextScriptResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextScriptResponse = None


if _SchemaGenerationVersionInfo is None:

    class GenerationVersionInfo(BaseModel):
        version: str
        name: str
        summary: str
        imagePromptStyle: str
        videoPromptStyle: str
        recommendedAspectRatios: list[str] = Field(default_factory=lambda: ["9:16", "16:9"])


else:
    GenerationVersionInfo = _SchemaGenerationVersionInfo


if _SchemaGenerationTextAnalysisModelInfo is None:

    class GenerationTextAnalysisModelInfo(BaseModel):
        value: str
        label: str
        description: str | None = None
        isDefault: bool = False
        provider: str | None = None
        family: str | None = None
        aliases: list[str] = Field(default_factory=list)


else:
    GenerationTextAnalysisModelInfo = _SchemaGenerationTextAnalysisModelInfo


if _SchemaGenerationVideoSizeOption is None:

    class GenerationVideoSizeOption(BaseModel):
        value: str
        label: str
        width: int
        height: int
        aspectRatio: str
        tier: str | None = None


else:
    GenerationVideoSizeOption = _SchemaGenerationVideoSizeOption


if _SchemaGenerationVideoModelOption is None:

    class GenerationVideoModelOption(BaseModel):
        key: str
        label: str
        description: str | None = None
        sizes: list[GenerationVideoSizeOption] = Field(default_factory=list)
        defaultSize: str | None = None
        durations: list[int] = Field(default_factory=list)
        defaultDurationSeconds: int | None = None
        durationMode: Literal["fixed", "discrete", "range"] = "fixed"
        durationMinSeconds: int | None = None
        durationMaxSeconds: int | None = None
        supportsAudio: bool = False
        supportsShotType: bool = False


else:
    GenerationVideoModelOption = _SchemaGenerationVideoModelOption


if _SchemaGenerationOptionsResponse is None:

    class GenerationOptionsResponse(BaseModel):
        versions: list[int] = Field(default_factory=list)
        versionDetails: list[dict[str, Any]] = Field(default_factory=list)
        defaultVersion: int | None = None
        stylePresets: list[dict[str, Any]] = Field(default_factory=list)
        imageSizes: list[dict[str, Any]] = Field(default_factory=list)
        textAnalysisModels: list[dict[str, Any]] = Field(default_factory=list)
        defaultTextAnalysisModel: str | None = None
        videoModels: list[dict[str, Any]] = Field(default_factory=list)
        defaultVideoModel: str | None = None
        videoSizes: list[dict[str, Any]] = Field(default_factory=list)
        videoDurations: list[dict[str, Any]] = Field(default_factory=list)
        defaultStylePreset: str | None = None
        defaultImageSize: str | None = None
        defaultVideoSize: str | None = None
        defaultVideoDurationSeconds: int | None = None


else:
    GenerationOptionsResponse = _SchemaGenerationOptionsResponse


if _SchemaGenerateTextMediaRequest is None:

    class GenerateTextMediaRequest(BaseModel):
        prompt: str = Field(min_length=1, max_length=3000)
        version: str = "v1"
        textAnalysisModel: str | None = None
        providerModel: str | None = None
        videoModel: str | None = None
        aspectRatio: str = "9:16"
        durationSeconds: float = Field(default=4.0, ge=1.0, le=30.0)
        minDurationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
        maxDurationSeconds: float | None = Field(default=None, ge=1.0, le=120.0)
        seed: int | None = None
        extras: dict[str, Any] = Field(default_factory=dict)

        @model_validator(mode="before")
        @classmethod
        def _migrate_aliases(cls, data: Any) -> Any:
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            if not isinstance(data, dict):
                return data
            payload = dict(data)
            payload.setdefault("version", payload.get("generationVersion") or payload.get("profileVersion") or "v1")
            payload.setdefault("aspectRatio", payload.get("aspect_ratio") or payload.get("ratio") or "9:16")
            if "durationSeconds" not in payload:
                payload["durationSeconds"] = payload.get("duration") or payload.get("videoDuration") or 4.0
            payload.setdefault("minDurationSeconds", payload.get("minDuration") or payload.get("minVideoDurationSeconds"))
            payload.setdefault("maxDurationSeconds", payload.get("maxDuration") or payload.get("maxVideoDurationSeconds"))
            payload.setdefault("extras", payload.get("metadata") or {})
            if "videoModel" not in payload and payload.get("providerModel"):
                payload["videoModel"] = payload.get("providerModel")
            return payload

        @model_validator(mode="after")
        def _normalize(self) -> "GenerateTextMediaRequest":
            normalized_version = (self.version or "v1").strip().lower()
            if not normalized_version.startswith("v"):
                normalized_version = f"v{normalized_version}"
            self.version = normalized_version
            ratio = (self.aspectRatio or "9:16").strip()
            self.aspectRatio = ratio if ratio in {"9:16", "16:9"} else "9:16"
            self.textAnalysisModel = (self.textAnalysisModel or "").strip() or None
            self.providerModel = (self.providerModel or "").strip() or None
            self.videoModel = (self.videoModel or "").strip() or None
            self.durationSeconds = float(min(30.0, max(1.0, self.durationSeconds)))
            if self.minDurationSeconds is None:
                self.minDurationSeconds = self.durationSeconds
            if self.maxDurationSeconds is None:
                self.maxDurationSeconds = self.durationSeconds
            return self


else:
    GenerateTextMediaRequest = _SchemaGenerateTextMediaRequest


if _SchemaGenerateTextMediaResponse is None:

    class GenerateTextMediaResponse(BaseModel):
        generationId: str
        mediaType: Literal["image", "video"]
        prompt: str
        shapedPrompt: str
        source: str
        filePath: str
        fileUrl: str
        mimeType: str
        metadata: dict[str, Any] = Field(default_factory=dict)


else:
    GenerateTextMediaResponse = _SchemaGenerateTextMediaResponse


if _SchemaProbeTextAnalysisModelRequest is None:

    class ProbeTextAnalysisModelRequest(BaseModel):
        textAnalysisModel: str | None = None


else:
    ProbeTextAnalysisModelRequest = _SchemaProbeTextAnalysisModelRequest


if _SchemaProbeTextAnalysisModelResponse is None:

    class ProbeTextAnalysisModelResponse(BaseModel):
        ready: bool = True
        requestedModel: str
        resolvedModel: str
        provider: str
        family: str | None = None
        mode: str
        endpointHost: str
        latencyMs: int
        messagePreview: str | None = None
        checkedAt: str


else:
    ProbeTextAnalysisModelResponse = _SchemaProbeTextAnalysisModelResponse


if _SchemaGenerateTextScriptRequest is None:

    class GenerateTextScriptRequest(BaseModel):
        text: str = Field(min_length=1, max_length=1_000_000)
        visualStyle: str | None = Field(default=None, max_length=120)
        textAnalysisModel: str | None = Field(default=None, max_length=120)

        @model_validator(mode="after")
        def _normalize(self) -> "GenerateTextScriptRequest":
            self.text = self.text.strip()
            if not self.text:
                raise ValueError("text must be non-empty")
            self.visualStyle = (self.visualStyle or "").strip() or None
            self.textAnalysisModel = (self.textAnalysisModel or "").strip() or None
            return self


else:
    GenerateTextScriptRequest = _SchemaGenerateTextScriptRequest


if _SchemaGenerateTextScriptResponse is None:

    class GenerateTextScriptResponse(BaseModel):
        id: str
        sourceText: str
        visualStyle: str
        outputFormat: Literal["markdown"] = "markdown"
        scriptMarkdown: str
        markdownFilePath: str | None = None
        markdownFileUrl: str | None = None
        downloadUrl: str | None = None
        source: str
        createdAt: str
        modelInfo: dict[str, Any] = Field(default_factory=dict)
        callChain: list[dict[str, Any]] = Field(default_factory=list)
        metadata: dict[str, Any] = Field(default_factory=dict)


else:
    GenerateTextScriptResponse = _SchemaGenerateTextScriptResponse


@dataclass(frozen=True)
class _VersionProfile:
    version: str
    name: str
    summary: str
    image_prompt_style: str
    video_prompt_style: str
    image_gradient_start: str
    image_gradient_end: str
    video_color: str


@dataclass(frozen=True)
class _VideoSizeProfile:
    value: str
    width: int
    height: int
    label: str
    aspect_ratio: str
    tier: str | None = None


@dataclass(frozen=True)
class _VideoModelProfile:
    key: str
    label: str
    summary: str
    sizes: tuple[_VideoSizeProfile, ...]
    default_size: str
    durations: tuple[int, ...]
    default_duration_seconds: int
    duration_mode: Literal["fixed", "discrete", "range"] = "fixed"
    duration_min_seconds: int | None = None
    duration_max_seconds: int | None = None
    prompt_max_chars: int = 1500
    supports_audio: bool = False
    supports_shot_type: bool = False


@dataclass(frozen=True)
class _TextAnalysisModelProfile:
    key: str
    label: str
    provider: str
    summary: str
    family: str
    endpoint: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class _VideoModelSpec:
    name: str
    label: str
    supported_sizes: tuple[str, ...]
    min_duration_seconds: int
    max_duration_seconds: int
    default_duration_seconds: int
    prompt_limit: int
    allowed_durations: tuple[int, ...] = ()
    provider_kind: Literal["dashscope", "qwen_vl_workflow", "seeddance"] = "dashscope"
    backend_model_name: str | None = None

    @property
    def is_fixed_duration(self) -> bool:
        allowed = self.allowed_durations
        if allowed:
            return len(allowed) == 1
        return self.min_duration_seconds == self.max_duration_seconds


_PROFILES: list[_VersionProfile] = [
    _VersionProfile(
        version="v1",
        name="Cinematic Realism",
        summary="Natural light, realistic textures, strong depth.",
        image_prompt_style="Create a cinematic still with realistic materials, layered foreground-midground-background, and controlled depth of field.",
        video_prompt_style="Create a cinematic shot plan with smooth push-in motion, realistic lighting evolution, and grounded camera movement.",
        image_gradient_start="#0f172a",
        image_gradient_end="#1d4ed8",
        video_color="#1d4ed8",
    ),
    _VersionProfile(
        version="v2",
        name="Anime Illustration",
        summary="Graphic edges, stylized expression, bright tones.",
        image_prompt_style="Create an anime key visual with clean line work, expressive framing, and high-contrast cel-shading.",
        video_prompt_style="Create an anime scene beat with punchy motion arcs, expressive framing changes, and energetic cuts.",
        image_gradient_start="#1f2937",
        image_gradient_end="#db2777",
        video_color="#db2777",
    ),
    _VersionProfile(
        version="v3",
        name="Minimal Editorial",
        summary="Clean composition, whitespace, premium layout.",
        image_prompt_style="Create a minimal editorial image with disciplined negative space, clear subject isolation, and magazine-grade composition.",
        video_prompt_style="Create an editorial motion concept with slow deliberate transitions, typography-friendly spacing, and elegant pacing.",
        image_gradient_start="#111827",
        image_gradient_end="#4b5563",
        video_color="#4b5563",
    ),
    _VersionProfile(
        version="v4",
        name="Neon Cyberpunk",
        summary="Neon glow, rain reflections, futuristic tension.",
        image_prompt_style="Create a cyberpunk frame with neon rim light, reflective surfaces, and atmospheric haze.",
        video_prompt_style="Create a cyberpunk shot sequence with parallax neon signage, wet-surface reflections, and dynamic camera drift.",
        image_gradient_start="#0f172a",
        image_gradient_end="#7c3aed",
        video_color="#7c3aed",
    ),
    _VersionProfile(
        version="v5",
        name="Watercolor Dream",
        summary="Soft pigment flow, poetic textures, airy mood.",
        image_prompt_style="Create a watercolor-styled image with pigment bleeding, soft edges, and a dreamy atmospheric palette.",
        video_prompt_style="Create a watercolor motion concept with gentle transitions, fluid texture shifts, and calm rhythm.",
        image_gradient_start="#0c4a6e",
        image_gradient_end="#22c55e",
        video_color="#22c55e",
    ),
    _VersionProfile(
        version="v6",
        name="Product Commercial",
        summary="Hero product focus, polished ad framing.",
        image_prompt_style="Create a product hero shot with premium reflections, controlled studio lighting, and conversion-focused composition.",
        video_prompt_style="Create a product ad sequence with feature-reveal beats, clean motion cues, and commercial pacing.",
        image_gradient_start="#172554",
        image_gradient_end="#0ea5e9",
        video_color="#0ea5e9",
    ),
    _VersionProfile(
        version="v7",
        name="Documentary Natural",
        summary="Authentic tone, observational framing, grounded.",
        image_prompt_style="Create a documentary-style still with natural light, authentic moment capture, and environmental context.",
        video_prompt_style="Create a documentary beat plan with observational handheld feel, practical movement, and honest pacing.",
        image_gradient_start="#1f2937",
        image_gradient_end="#15803d",
        video_color="#15803d",
    ),
    _VersionProfile(
        version="v8",
        name="Fantasy Matte",
        summary="Epic scale, layered atmosphere, mythic tone.",
        image_prompt_style="Create a fantasy matte frame with grand scale, volumetric atmosphere, and dramatic silhouettes.",
        video_prompt_style="Create an epic fantasy sequence with scale-establishing moves, atmospheric build-up, and mythic energy.",
        image_gradient_start="#312e81",
        image_gradient_end="#a21caf",
        video_color="#a21caf",
    ),
    _VersionProfile(
        version="v9",
        name="Retro Vaporwave",
        summary="Nostalgic synth aesthetics, geometric boldness.",
        image_prompt_style="Create a vaporwave visual with retro gradients, geometric motifs, and nostalgic digital texture.",
        video_prompt_style="Create a retro synthwave motion concept with rhythmic geometric transitions and nostalgic neon timing.",
        image_gradient_start="#1e1b4b",
        image_gradient_end="#ec4899",
        video_color="#ec4899",
    ),
    _VersionProfile(
        version="v10",
        name="Bold Kinetic Type",
        summary="Strong typography, aggressive rhythm, modern social style.",
        image_prompt_style="Create a typographic hero image with oversized lettering, high contrast hierarchy, and modern social-first framing.",
        video_prompt_style="Create a kinetic type video concept with bold text beats, high-impact timing, and punchy visual accents.",
        image_gradient_start="#111827",
        image_gradient_end="#f97316",
        video_color="#f97316",
    ),
]

_VIDEO_SIZE_480P_16_9 = _VideoSizeProfile(
    value="832x480",
    width=832,
    height=480,
    label="832 × 480",
    aspect_ratio="26:15",
    tier="480p",
)
_VIDEO_SIZE_720P_16_9 = _VideoSizeProfile(
    value="1280x720",
    width=1280,
    height=720,
    label="1280 × 720",
    aspect_ratio="16:9",
    tier="720p",
)
_VIDEO_SIZE_720P_9_16 = _VideoSizeProfile(
    value="720x1280",
    width=720,
    height=1280,
    label="720 × 1280",
    aspect_ratio="9:16",
    tier="720p",
)
_VIDEO_SIZE_1080P_16_9 = _VideoSizeProfile(
    value="1920x1080",
    width=1920,
    height=1080,
    label="1920 × 1080",
    aspect_ratio="16:9",
    tier="1080p",
)
_VIDEO_SIZE_1080P_9_16 = _VideoSizeProfile(
    value="1080x1920",
    width=1080,
    height=1920,
    label="1080 × 1920",
    aspect_ratio="9:16",
    tier="1080p",
)

_VIDEO_MODEL_PROFILES: tuple[_VideoModelProfile, ...] = (
    _VideoModelProfile(
        key="wan2.6-i2v",
        label="Wan 2.6 图生视频",
        summary="阿里云公开文档中的 Wan 2.6 图生视频模型，支持 720p/1080p 与 2-15 秒生成。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(2, 3, 4, 5, 6, 8, 10, 12, 15),
        default_duration_seconds=5,
        duration_mode="range",
        duration_min_seconds=2,
        duration_max_seconds=15,
        prompt_max_chars=1500,
        supports_audio=True,
        supports_shot_type=True,
    ),
    _VideoModelProfile(
        key="wan2.6-t2v",
        label="Wan 2.6 文生视频",
        summary="阿里云公开文档推荐的新版文生视频模型，支持 720p/1080p 与 2-15 秒生成。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(2, 3, 4, 5, 6, 8, 10, 12, 15),
        default_duration_seconds=5,
        duration_mode="range",
        duration_min_seconds=2,
        duration_max_seconds=15,
        prompt_max_chars=1500,
        supports_audio=True,
        supports_shot_type=True,
    ),
    _VideoModelProfile(
        key="wan2.6-t2v-us",
        label="Wan 2.6 文生视频 US",
        summary="阿里云公开文档中的美国地域文生视频模型，支持 720p/1080p 与 5、10、15 秒生成。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(5, 10, 15),
        default_duration_seconds=5,
        duration_mode="discrete",
        prompt_max_chars=1500,
        supports_audio=True,
        supports_shot_type=True,
    ),
    _VideoModelProfile(
        key="wan2.5-t2v-preview",
        label="Wan 2.5 文生视频 Preview",
        summary="公开视频文档中的预览模型，支持 480p/720p/1080p 与 5 或 10 秒生成。",
        sizes=(
            _VIDEO_SIZE_480P_16_9,
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(5, 10),
        default_duration_seconds=5,
        duration_mode="discrete",
        prompt_max_chars=1500,
        supports_audio=True,
    ),
    _VideoModelProfile(
        key="wan2.2-t2v-plus",
        label="Wan 2.2 文生视频 Plus",
        summary="稳定的高质量文生视频模型，公开文档当前支持固定 5 秒生成。",
        sizes=(
            _VIDEO_SIZE_480P_16_9,
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(5,),
        default_duration_seconds=5,
        duration_mode="fixed",
        prompt_max_chars=800,
    ),
    _VideoModelProfile(
        key="wanx2.1-t2v-turbo",
        label="Wanx 2.1 文生视频 Turbo",
        summary="更快的文生视频模型，公开文档当前支持固定 5 秒生成。",
        sizes=(
            _VIDEO_SIZE_480P_16_9,
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
        ),
        default_size=_VIDEO_SIZE_720P_16_9.value,
        durations=(5,),
        default_duration_seconds=5,
        duration_mode="fixed",
        prompt_max_chars=800,
    ),
    _VideoModelProfile(
        key="wanx2.1-t2v-plus",
        label="Wanx 2.1 文生视频 Plus",
        summary="质量优先的 Wanx 2.1 文生视频模型，公开文档当前支持固定 5 秒生成。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
        ),
        default_size=_VIDEO_SIZE_720P_16_9.value,
        durations=(5,),
        default_duration_seconds=5,
        duration_mode="fixed",
        prompt_max_chars=800,
    ),
    _VideoModelProfile(
        key="qwen-vl",
        label="Qwen-VL 视频工作流",
        summary="阿里 Qwen-VL 提示词理解 + 百炼视频生成链路，适合复杂描述理解。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(2, 3, 4, 5, 6, 8, 10, 12, 15),
        default_duration_seconds=5,
        duration_mode="range",
        duration_min_seconds=2,
        duration_max_seconds=15,
        prompt_max_chars=1500,
        supports_audio=True,
        supports_shot_type=True,
    ),
    _VideoModelProfile(
        key="seeddance-1.5-pro",
        label="SeedDance 1.5 Pro",
        summary="SeedDance 1.5 Pro 图生视频模型（异步任务接口）。",
        sizes=(
            _VIDEO_SIZE_720P_16_9,
            _VIDEO_SIZE_720P_9_16,
            _VIDEO_SIZE_1080P_16_9,
            _VIDEO_SIZE_1080P_9_16,
        ),
        default_size=_VIDEO_SIZE_1080P_16_9.value,
        durations=(5,),
        default_duration_seconds=5,
        duration_mode="fixed",
        prompt_max_chars=1500,
        supports_audio=True,
        supports_shot_type=True,
    ),
)

_TEXT_ANALYSIS_MODEL_PROFILES: tuple[_TextAnalysisModelProfile, ...] = (
    _TextAnalysisModelProfile(
        key="gpt-5.4",
        label="GPT-5.4",
        provider="openai",
        family="gpt",
        summary="OpenAI ChatGPT key 模式，适合人物、对白、语境和剧情理解。",
        endpoint="https://api.openai.com/v1/chat/completions",
        aliases=("gpt5.4", "gpt-5", "chatgpt", "chatgpt-key"),
    ),
    _TextAnalysisModelProfile(
        key="qwen3.6-plus",
        label="Qwen 3.6 Plus",
        provider="aliyun-bailian",
        family="qwen",
        summary="阿里 Qwen 文本分析模型，兼容现有百炼 key 配置。",
        aliases=("qwen", "qwen3.6-plus", "qwen-max-latest", "qwen-max", "qwen-plus"),
    ),
)

_VIDEO_MODELS: dict[str, _VideoModelSpec] = {
    "wan2.6-i2v": _VideoModelSpec(
        name="wan2.6-i2v",
        label="Wan 2.6 图生视频",
        supported_sizes=(
            "832*480",
            "480*832",
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=2,
        max_duration_seconds=15,
        default_duration_seconds=5,
        prompt_limit=1500,
    ),
    "wan2.6-t2v": _VideoModelSpec(
        name="wan2.6-t2v",
        label="Wan 2.6 文生视频",
        supported_sizes=(
            "832*480",
            "480*832",
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=2,
        max_duration_seconds=15,
        default_duration_seconds=5,
        prompt_limit=1500,
    ),
    "wan2.6-t2v-us": _VideoModelSpec(
        name="wan2.6-t2v-us",
        label="Wan 2.6 文生视频 US",
        supported_sizes=(
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=5,
        max_duration_seconds=15,
        default_duration_seconds=5,
        prompt_limit=1500,
        allowed_durations=(5, 10, 15),
    ),
    "wan2.5-t2v-preview": _VideoModelSpec(
        name="wan2.5-t2v-preview",
        label="Wan 2.5 文生视频 Preview",
        supported_sizes=(
            "832*480",
            "480*832",
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=5,
        max_duration_seconds=10,
        default_duration_seconds=5,
        prompt_limit=1500,
    ),
    "wan2.2-t2v-plus": _VideoModelSpec(
        name="wan2.2-t2v-plus",
        label="Wan 2.2 文生视频 Plus",
        supported_sizes=(
            "832*480",
            "480*832",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=5,
        max_duration_seconds=5,
        default_duration_seconds=5,
        prompt_limit=800,
    ),
    "wanx2.1-t2v-turbo": _VideoModelSpec(
        name="wanx2.1-t2v-turbo",
        label="WanX 2.1 文生视频 Turbo",
        supported_sizes=(
            "832*480",
            "480*832",
            "1280*720",
            "720*1280",
        ),
        min_duration_seconds=5,
        max_duration_seconds=5,
        default_duration_seconds=5,
        prompt_limit=800,
    ),
    "wanx2.1-t2v-plus": _VideoModelSpec(
        name="wanx2.1-t2v-plus",
        label="WanX 2.1 文生视频 Plus",
        supported_sizes=(
            "1280*720",
            "720*1280",
        ),
        min_duration_seconds=5,
        max_duration_seconds=5,
        default_duration_seconds=5,
        prompt_limit=800,
    ),
    "qwen-vl": _VideoModelSpec(
        name="qwen-vl",
        label="Qwen-VL 视频工作流",
        supported_sizes=(
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=2,
        max_duration_seconds=15,
        default_duration_seconds=5,
        prompt_limit=1500,
        provider_kind="qwen_vl_workflow",
        backend_model_name="wan2.6-t2v",
    ),
    "seeddance-1.5-pro": _VideoModelSpec(
        name="seeddance-1.5-pro",
        label="SeedDance 1.5 Pro",
        supported_sizes=(
            "864*496",
            "496*864",
            "1280*720",
            "720*1280",
            "1920*1080",
            "1080*1920",
        ),
        min_duration_seconds=5,
        max_duration_seconds=5,
        default_duration_seconds=5,
        prompt_limit=1500,
        allowed_durations=(5,),
        provider_kind="seeddance",
        backend_model_name="doubao-seedance-1-5-pro-251215",
    ),
}

_VIDEO_MODEL_ALIASES = {
    "wan2.6-t2v-plus": "wan2.6-t2v",
    "wan2.6-t2v-turbo": "wan2.6-t2v",
    "wan2.5-t2v-plus": "wan2.5-t2v-preview",
    "wan2.5-t2v-turbo": "wan2.5-t2v-preview",
    "wan2.1-t2v-plus": "wanx2.1-t2v-plus",
    "wan2.1-t2v-turbo": "wanx2.1-t2v-turbo",
    "qwen-vl-workflow": "qwen-vl",
    "qwen-vl-plus": "qwen-vl",
    "qwen-vl-plus-latest": "qwen-vl",
    "qwen-vl-max-latest": "qwen-vl",
    "seeddance1.5pro": "seeddance-1.5-pro",
    "seeddance-1.5-pro": "seeddance-1.5-pro",
    "seed-dance-1.5-pro": "seeddance-1.5-pro",
    "seeddance-1-5-pro": "seeddance-1.5-pro",
    "doubao-seedance-1-5-pro-251215": "seeddance-1.5-pro",
}
_SEEDREAM_IMAGE_MODEL_4_5 = "doubao-seedream-4-5-251128"
_SEEDREAM_IMAGE_MODEL_5_0 = "doubao-seedream-5-0-260128"
_DEFAULT_SEEDREAM_IMAGE_MODEL = _SEEDREAM_IMAGE_MODEL_4_5
_SEEDREAM_IMAGE_MODEL_ALIASES = {
    "doubao-seedream-4.5": _SEEDREAM_IMAGE_MODEL_4_5,
    "doubao-seedream-4-5": _SEEDREAM_IMAGE_MODEL_4_5,
    "seedream-4.5": _SEEDREAM_IMAGE_MODEL_4_5,
    "seedream-4-5": _SEEDREAM_IMAGE_MODEL_4_5,
    "doubao-seedream-5.0-lite": _SEEDREAM_IMAGE_MODEL_5_0,
    "doubao-seedream-5-0-lite": _SEEDREAM_IMAGE_MODEL_5_0,
    "doubao-seedream-5.0": _SEEDREAM_IMAGE_MODEL_5_0,
    "doubao-seedream-5-0": _SEEDREAM_IMAGE_MODEL_5_0,
    "seedream-5.0-lite": _SEEDREAM_IMAGE_MODEL_5_0,
    "seedream-5-0-lite": _SEEDREAM_IMAGE_MODEL_5_0,
    "seedream-5.0": _SEEDREAM_IMAGE_MODEL_5_0,
    "seedream-5-0": _SEEDREAM_IMAGE_MODEL_5_0,
}
_DEFAULT_IMAGE_SIZES = [
    {"value": "768x768", "label": "768 × 768", "width": 768, "height": 768},
    {"value": "1024x1024", "label": "1024 × 1024", "width": 1024, "height": 1024},
    {"value": "1365x768", "label": "1365 × 768", "width": 1365, "height": 768},
]


def _normalize_video_model_name(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    return _VIDEO_MODEL_ALIASES.get(normalized, normalized)


def _normalize_seedream_image_model_name(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return _DEFAULT_SEEDREAM_IMAGE_MODEL
    mapped = _SEEDREAM_IMAGE_MODEL_ALIASES.get(normalized)
    if mapped:
        return mapped
    if normalized.startswith("doubao-seedream-"):
        return normalized
    if normalized.startswith("seedream-"):
        return f"doubao-{normalized}"
    if "seedream" in normalized:
        return _DEFAULT_SEEDREAM_IMAGE_MODEL
    return normalized


def _looks_like_seedream_image_model(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False
    if "seedream" in normalized:
        return True
    return normalized in _SEEDREAM_IMAGE_MODEL_ALIASES


def _video_model_spec(model_name: str | None) -> _VideoModelSpec:
    normalized = _normalize_video_model_name(model_name)
    if normalized in _VIDEO_MODELS:
        return _VIDEO_MODELS[normalized]
    return _VIDEO_MODELS["wan2.6-i2v"]


def _video_size_profiles(spec: _VideoModelSpec) -> list[_VideoSizeProfile]:
    profiles: list[_VideoSizeProfile] = []
    for size in spec.supported_sizes:
        width = int(size.split("*", 1)[0])
        height = int(size.split("*", 1)[1])
        longest_edge = max(width, height)
        tier = "1080p" if longest_edge >= 1920 else "720p" if longest_edge >= 1280 else "480p"
        aspect_ratio = "16:9" if width >= height else "9:16"
        profiles.append(
            _VideoSizeProfile(
                value=size,
                width=width,
                height=height,
                label=f"{width} × {height}",
                aspect_ratio=aspect_ratio,
                tier=tier,
            )
        )
    return profiles


def _video_size_options(spec: _VideoModelSpec) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for size in _video_size_profiles(spec):
        options.append(
            {
                "value": size.value.replace("*", "x"),
                "label": f"{size.width} × {size.height}",
                "width": size.width,
                "height": size.height,
                "aspectRatio": size.aspect_ratio,
                "tier": size.tier,
            }
        )
    return options


def _video_duration_options(spec: _VideoModelSpec) -> list[dict[str, Any]]:
    durations = list(spec.allowed_durations) if spec.allowed_durations else list(range(spec.min_duration_seconds, spec.max_duration_seconds + 1))
    if spec.is_fixed_duration:
        durations = [spec.default_duration_seconds]
    return [{"value": duration, "label": f"{duration} 秒"} for duration in durations]


def _video_model_options(
    default_model_name: str | None = None,
    specs: Iterable[_VideoModelSpec] | None = None,
) -> list[dict[str, Any]]:
    default_model_name = _normalize_video_model_name(default_model_name) or "wan2.6-i2v"
    options: list[dict[str, Any]] = []
    for spec in specs or _VIDEO_MODELS.values():
        provider_label = "阿里云百炼"
        if spec.provider_kind == "qwen_vl_workflow":
            provider_label = "阿里 Qwen-VL 工作流"
        elif spec.provider_kind == "seeddance":
            provider_label = "火山引擎 SeedDance 1.5 Pro"
        generation_mode: Literal["t2v", "i2v", "vl"] = "t2v"
        if spec.provider_kind == "qwen_vl_workflow":
            generation_mode = "vl"
        elif spec.name in {"wan2.6-i2v", "seeddance-1.5-pro"}:
            generation_mode = "i2v"
        options.append(
            {
                "value": spec.name,
                "label": spec.label,
                "description": f"{provider_label} 视频模型 {spec.name}",
                "isDefault": spec.name == default_model_name,
                "provider": (
                    "volcengine"
                    if spec.provider_kind == "seeddance"
                    else "aliyun-bailian"
                    if spec.provider_kind == "qwen_vl_workflow"
                    else "aliyun-bailian"
                ),
                "family": "seeddance" if spec.provider_kind == "seeddance" else "qwen" if spec.provider_kind == "qwen_vl_workflow" else "wan",
                "generationMode": generation_mode,
                "supportedSizes": [size.replace("*", "x") for size in spec.supported_sizes],
                "supportedDurations": [item["value"] for item in _video_duration_options(spec)],
                "aliases": [alias for alias, normalized in _VIDEO_MODEL_ALIASES.items() if normalized == spec.name],
            }
        )
    return options


def _normalize_text_analysis_model_name(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    for profile in _TEXT_ANALYSIS_MODEL_PROFILES:
        if normalized == profile.key.lower():
            return profile.key
        if normalized in {alias.lower() for alias in profile.aliases}:
            return profile.key
    return normalized


def _text_analysis_model_profile(model_name: str | None) -> _TextAnalysisModelProfile:
    normalized = _normalize_text_analysis_model_name(model_name)
    for profile in _TEXT_ANALYSIS_MODEL_PROFILES:
        if profile.key == normalized:
            return profile
    return _TEXT_ANALYSIS_MODEL_PROFILES[0]


def _video_size_catalog(specs: Iterable[_VideoModelSpec] | None = None) -> list[dict[str, Any]]:
    size_map: dict[str, dict[str, Any]] = {}
    for spec in specs or _VIDEO_MODELS.values():
        for size in _video_size_options(spec):
            key = size["value"]
            entry = size_map.setdefault(
                key,
                {
                    **size,
                    "supportedModels": [],
                },
            )
            entry["supportedModels"].append(spec.name)
    return sorted(size_map.values(), key=lambda item: (item["tier"], item["width"], item["height"]))


def _video_duration_catalog(specs: Iterable[_VideoModelSpec] | None = None) -> list[dict[str, Any]]:
    duration_map: dict[int, dict[str, Any]] = {}
    for spec in specs or _VIDEO_MODELS.values():
        for duration in _video_duration_options(spec):
            value = int(duration["value"])
            entry = duration_map.setdefault(
                value,
                {
                    "value": value,
                    "label": duration["label"],
                    "supportedModels": [],
                },
            )
            entry["supportedModels"].append(spec.name)
    return [duration_map[key] for key in sorted(duration_map)]


DEFAULT_SCRIPT_VISUAL_STYLE = "AI 自动决策"


def _infer_script_visual_style(source_text: str) -> str:
    text = source_text.strip()
    suspense_hits = sum(keyword in text for keyword in ["暴雨", "失踪", "秘密", "录音", "深夜", "追逐", "血", "逃", "悬疑", "惊悚"])
    action_hits = sum(keyword in text for keyword in ["追逐", "枪", "爆炸", "战斗", "撞", "冲", "逃亡", "对峙"])
    fantasy_hits = sum(keyword in text for keyword in ["未来", "赛博", "机械", "星际", "宇宙", "异界", "魔法", "神"])
    romance_hits = sum(keyword in text for keyword in ["告白", "心动", "拥抱", "重逢", "恋", "想念", "婚礼"])
    healing_hits = sum(keyword in text for keyword in ["日常", "午后", "街角", "家", "治愈", "成长", "回忆", "风"])

    if suspense_hits >= max(action_hits, fantasy_hits, romance_hits, healing_hits) and suspense_hits > 0:
        return "冷色悬疑电影写实风格"
    if action_hits >= max(fantasy_hits, romance_hits, healing_hits) and action_hits > 0:
        return "高对比动作电影风格"
    if fantasy_hits >= max(romance_hits, healing_hits) and fantasy_hits > 0:
        return "奇幻电影概念艺术风格"
    if romance_hits >= healing_hits and romance_hits > 0:
        return "柔光情绪电影风格"
    if healing_hits > 0:
        return "生活流治愈电影风格"
    return "写实电影叙事风格"


def _estimate_script_shot_targets(source_text: str) -> tuple[int, int]:
    normalized = source_text.strip()
    text_length = len(normalized)
    if text_length <= 2_000:
        recommended = 14
    elif text_length <= 5_000:
        recommended = 22
    elif text_length <= 12_000:
        recommended = 32
    elif text_length <= 25_000:
        recommended = 46
    elif text_length <= 50_000:
        recommended = 64
    elif text_length <= 80_000:
        recommended = 82
    else:
        recommended = 98
    dialogue_marker_count = sum(normalized.count(marker) for marker in ("“", "”", "\"", "「", "」"))
    dialogue_pair_estimate = dialogue_marker_count // 2
    dialogue_bonus = min(36, dialogue_pair_estimate // 5)
    recommended = min(140, recommended + dialogue_bonus)
    minimum = max(12, int(round(recommended * 0.75)))
    return minimum, recommended


def _script_output_token_candidates(configured_max_tokens: int) -> list[int]:
    configured = max(512, int(configured_max_tokens or 0))
    if configured >= 3_200:
        return [configured]
    candidates = [9_600, 8_000, 6_400, 4_800, 3_200, configured]
    ordered: list[int] = []
    seen: set[int] = set()
    for item in candidates:
        if item in seen:
            continue
        ordered.append(item)
        seen.add(item)
    return ordered


class TextGenerationEngine:
    def __init__(
        self,
        settings: Settings,
        storage: MediaStorage,
        *,
        ffmpeg_bin: str = "ffmpeg",
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.ffmpeg_bin = ffmpeg_bin
        self._profiles = {profile.version: profile for profile in _PROFILES}
        self._video_models = {profile.key: profile for profile in _VIDEO_MODEL_PROFILES}
        self._text_analysis_models = {profile.key: profile for profile in _TEXT_ANALYSIS_MODEL_PROFILES}
        self._image_module = ImageGenerationModule(self)
        self._video_module = VideoGenerationModule(self)
        self._image_module.bind_video_module(self._video_module)
        self._video_module.bind_image_module(self._image_module)

    def list_versions(self) -> GenerationOptionsResponse:
        return self.get_generation_options()

    def _configured_text_analysis_models(self) -> list[_TextAnalysisModelProfile]:
        raw = str(getattr(self.settings.model, "text_analysis_models", "") or "").strip()
        if not raw:
            return list(_TEXT_ANALYSIS_MODEL_PROFILES)
        ordered: list[_TextAnalysisModelProfile] = []
        seen: set[str] = set()
        items: list[str] = []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for entry in parsed:
                        if isinstance(entry, str):
                            items.append(entry)
                        elif isinstance(entry, dict):
                            items.append(str(entry.get("value") or entry.get("model") or "").strip())
            except Exception:
                items = []
        if not items:
            items = [item.strip() for item in raw.split(",")]
        for item in items:
            key = _normalize_text_analysis_model_name(item)
            profile = self._text_analysis_models.get(key)
            if profile is None or profile.key in seen:
                continue
            ordered.append(profile)
            seen.add(profile.key)
        if not ordered:
            return list(_TEXT_ANALYSIS_MODEL_PROFILES)
        for profile in _TEXT_ANALYSIS_MODEL_PROFILES:
            if profile.key not in seen:
                ordered.append(profile)
        return ordered

    def _default_text_analysis_model(self) -> _TextAnalysisModelProfile:
        configured = self._configured_text_analysis_models()
        preferred_key = _normalize_text_analysis_model_name(self.settings.model.text_analysis_model_name)
        preferred = next((item for item in configured if item.key == preferred_key), None)
        return preferred or configured[0]

    def _configured_video_model_specs(self) -> list[_VideoModelSpec]:
        raw = str(getattr(self.settings.model, "video_models", "") or "").strip()
        items: list[str] = []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for entry in parsed:
                        if isinstance(entry, str):
                            items.append(entry)
                        elif isinstance(entry, dict):
                            items.append(str(entry.get("value") or entry.get("model") or "").strip())
            except Exception:
                items = []
        if not items and raw:
            items = [item.strip() for item in raw.split(",")]

        ordered: list[_VideoModelSpec] = []
        seen: set[str] = set()
        for item in items:
            key = _normalize_video_model_name(item)
            spec = _VIDEO_MODELS.get(key)
            if spec is None or spec.name in seen:
                continue
            ordered.append(spec)
            seen.add(spec.name)
        if ordered:
            return ordered
        return [self._resolve_video_model_spec()]

    def _default_video_model_spec(self) -> _VideoModelSpec:
        configured = self._configured_video_model_specs()
        preferred_key = _normalize_video_model_name(self.settings.model.video_model_name)
        preferred = next((item for item in configured if item.name == preferred_key), None)
        return preferred or configured[0]

    def _text_analysis_model_options(self) -> list[dict[str, Any]]:
        default_model = self._default_text_analysis_model()
        return [
            {
                "value": profile.key,
                "label": profile.label,
                "description": profile.summary,
                "isDefault": profile.key == default_model.key,
                "provider": profile.provider,
                "family": profile.family,
                "aliases": list(profile.aliases),
            }
            for profile in self._configured_text_analysis_models()
        ]

    def _resolve_text_analysis_model(self, explicit_model: str | None = None) -> _TextAnalysisModelProfile:
        key = _normalize_text_analysis_model_name(explicit_model) or _normalize_text_analysis_model_name(
            self.settings.model.text_analysis_model_name
        )
        return self._text_analysis_models.get(key) or self._default_text_analysis_model()

    def get_generation_options(self) -> GenerationOptionsResponse:
        version_details: list[GenerationVersionInfo] = []
        for profile in _PROFILES:
            description = (
                f"Image shaping: {profile.image_prompt_style} "
                f"Video shaping: {profile.video_prompt_style}"
            )
            if _SchemaGenerationVersionInfo is not None:
                payload = {
                    "version": int(profile.version.lstrip("v") or "1"),
                    "label": profile.name,
                    "isDefault": profile.version == "v1",
                    "supportedKinds": ["image", "video"],
                    "description": description,
                }
            else:
                payload = {
                    "version": profile.version,
                    "name": profile.name,
                    "summary": profile.summary,
                    "imagePromptStyle": profile.image_prompt_style,
                    "videoPromptStyle": profile.video_prompt_style,
                    "recommendedAspectRatios": ["9:16", "16:9"],
                }
            version_details.append(self._build_model(GenerationVersionInfo, payload))
        configured_video_specs = self._configured_video_model_specs()
        default_video_spec = self._default_video_model_spec()
        default_video_size = (
            default_video_spec.supported_sizes[0].replace("*", "x")
            if default_video_spec.supported_sizes
            else None
        )
        return self._build_model(
            GenerationOptionsResponse,
            {
                "versions": [int(profile.version.lstrip("v") or "1") for profile in _PROFILES],
                "versionDetails": [item.model_dump() if hasattr(item, "model_dump") else item for item in version_details],
                "stylePresets": [],
                "imageSizes": list(_DEFAULT_IMAGE_SIZES),
                "textAnalysisModels": self._text_analysis_model_options(),
                "defaultTextAnalysisModel": self._default_text_analysis_model().key,
                "videoModels": _video_model_options(default_video_spec.name, configured_video_specs),
                "videoSizes": _video_size_catalog(configured_video_specs),
                "videoDurations": _video_duration_catalog(configured_video_specs),
                "defaultVersion": 1,
                "defaultStylePreset": None,
                "defaultImageSize": "1024x1024",
                "defaultVideoDurationSeconds": default_video_spec.default_duration_seconds,
                "defaultVideoModel": default_video_spec.name,
                "defaultVideoSize": default_video_size,
            },
        )

    def list_options(self) -> GenerationOptionsResponse:
        return self.get_generation_options()

    def infer_video_provider(self, model_name: str) -> str:
        normalized_name = _normalize_video_model_name(model_name)
        spec = _VIDEO_MODELS.get(normalized_name)
        if spec is None:
            return "unknown"
        if spec.provider_kind == "seeddance":
            return "volcengine"
        if spec.provider_kind == "qwen_vl_workflow":
            return "aliyun-bailian"
        return "aliyun-bailian"

    def normalize_video_model_key(self, model_name: str) -> str:
        return _normalize_video_model_name(model_name)

    def get_model_aliases(self) -> dict[str, str]:
        return dict(_VIDEO_MODEL_ALIASES)

    def get_model_constraints(self) -> list[dict[str, Any]]:
        constraints: list[dict[str, Any]] = []
        for spec in _VIDEO_MODELS.values():
            max_width = 0
            max_height = 0
            for size in spec.supported_sizes:
                width, height = self._parse_video_size(size)
                max_width = max(max_width, width)
                max_height = max(max_height, height)
            constraints.append(
                {
                    "model": spec.name,
                    "mediaKind": "video",
                    "provider": self.infer_video_provider(spec.name),
                    "maxWidth": max_width or None,
                    "maxHeight": max_height or None,
                    "supportedSizes": [size.replace("*", "x") for size in spec.supported_sizes],
                    "minDurationSeconds": spec.min_duration_seconds,
                    "maxDurationSeconds": spec.max_duration_seconds,
                    "supportedDurations": (
                        list(spec.allowed_durations)
                        if spec.allowed_durations
                        else list(range(spec.min_duration_seconds, spec.max_duration_seconds + 1))
                    ),
                    "promptLimit": spec.prompt_limit,
                }
            )
        return constraints

    def get_video_model_usage(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        default_video_spec = self._default_video_model_spec()
        for option in _video_model_options(default_video_spec.name, self._configured_video_model_specs()):
            model_key = str(option.get("value") or "").strip()
            if not model_key:
                continue
            items.append(
                {
                    "model": model_key,
                    "label": str(option.get("label") or model_key),
                    "provider": self.infer_video_provider(model_key),
                    "used": 0,
                    "remaining": None,
                    "quota": None,
                    "usedDurationSeconds": 0.0,
                    "updatedAt": None,
                }
            )
        return {
            "generatedAt": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "items": items,
        }

    def generate_text_image(self, payload: Any) -> GenerateTextMediaResponse:
        return self._image_module.generate(payload)

    def generate_text_video(self, payload: Any) -> GenerateTextMediaResponse:
        return self._video_module.generate(payload)

    def probe_text_analysis_model(self, payload: Any = None) -> ProbeTextAnalysisModelResponse:
        request_obj = self._normalize_text_analysis_probe_request(payload)
        requested_model = str(request_obj.textAnalysisModel or "").strip() or None
        target = resolve_text_analysis_target(self.settings.model, requested_model)
        endpoint = str(target.endpoint or "").strip()
        api_key = str(target.api_key or "").strip()
        if not endpoint or not api_key:
            raise RuntimeError(f"text analysis provider is not configured for {target.model_name}")
        use_responses_api = should_use_responses_api(
            provider=target.provider,
            endpoint=endpoint,
            model_name=target.model_name,
        )
        request_endpoint = resolve_llm_request_endpoint(endpoint, use_responses_api=use_responses_api)
        body = build_text_request_body(
            model_name=target.model_name,
            system_prompt=self.settings.prompts.connectivity_probe,
            user_prompt="Reply with OK only.",
            temperature=0,
            max_tokens=12,
            use_responses_api=use_responses_api,
            enable_thinking=False,
        )
        request = urllib.request.Request(
            request_endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        started_at = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"text analysis probe timed out ({target.model_name}): {exc}") from exc
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            detail_text = truncate_text(detail.strip(), 240) or str(exc.reason or exc.code)
            raise RuntimeError(f"text analysis probe failed ({target.model_name}): HTTP {exc.code} {detail_text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"text analysis probe failed ({target.model_name}): {exc.reason or exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"text analysis probe failed ({target.model_name}): {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        payload_dict = self._parse_json_bytes(raw_response)
        content = self._extract_text_response(payload_dict, raw_response.decode("utf-8", errors="ignore")).strip()
        if not content:
            raise RuntimeError(f"text analysis probe response is empty ({target.model_name})")

        endpoint_host = ""
        try:
            endpoint_host = urllib.parse.urlparse(request_endpoint).netloc or request_endpoint
        except Exception:
            endpoint_host = request_endpoint

        return self._build_model(
            ProbeTextAnalysisModelResponse,
            {
                "ready": True,
                "requestedModel": requested_model or target.model_name,
                "resolvedModel": target.model_name,
                "provider": target.provider,
                "family": target.family,
                "mode": target.mode,
                "endpointHost": endpoint_host,
                "latencyMs": elapsed_ms,
                "messagePreview": truncate_text(content, 80) or content,
                "checkedAt": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            },
        )

    def generate_text_script(self, payload: Any) -> GenerateTextScriptResponse:
        request_obj = self._normalize_script_request(payload)
        return self._generate_script(request_obj)

    def generate_text_script_with_source_file(
        self,
        payload: Any,
        *,
        source_text_file_path: Path,
        source_text_file_name: str | None = None,
    ) -> GenerateTextScriptResponse:
        request_obj = self._normalize_script_request(payload)
        return self._generate_script(
            request_obj,
            source_text_file_path=source_text_file_path,
            source_text_file_name=source_text_file_name,
        )

    def _trace_call(
        self,
        call_chain: list[dict[str, Any]],
        *,
        stage: str,
        event: str,
        status: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "stage": stage,
            "event": event,
            "status": status,
            "message": message,
        }
        if details:
            entry["details"] = details
        call_chain.append(entry)

    def _is_openai_text_analysis_target(self, *, provider: str | None, endpoint: str | None) -> bool:
        provider_name = str(provider or "").strip().lower()
        if provider_name in {"openai", "chatgpt"}:
            return True
        parsed = urllib.parse.urlparse(str(endpoint or "").strip())
        host = (parsed.netloc or "").lower()
        return host.endswith("openai.com")

    def _openai_api_base(self, endpoint: str) -> str:
        normalized = str(endpoint or "").strip()
        if not normalized:
            return "https://api.openai.com/v1"
        marker = "/v1/"
        if marker in normalized:
            return normalized.split(marker, 1)[0] + "/v1"
        parsed = urllib.parse.urlparse(normalized)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/v1"
        return "https://api.openai.com/v1"

    def _build_multipart_form_data(
        self,
        *,
        fields: dict[str, str],
        file_field_name: str,
        file_name: str,
        file_bytes: bytes,
        file_content_type: str,
    ) -> tuple[bytes, str]:
        boundary = f"----ai-cut-{new_id('multipart')}"
        body = bytearray()
        for key, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"\r\n'
                f"Content-Type: {file_content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(file_bytes)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        return bytes(body), f"multipart/form-data; boundary={boundary}"

    def _upload_openai_input_file(
        self,
        *,
        api_base: str,
        api_key: str,
        source_text_file_path: Path,
        source_text_file_name: str | None,
        call_chain: list[dict[str, Any]],
    ) -> str:
        file_name = source_text_file_name or source_text_file_path.name
        file_bytes = source_text_file_path.read_bytes()
        content_type = mimetypes.guess_type(file_name)[0] or "text/plain"
        body, multipart_content_type = self._build_multipart_form_data(
            fields={"purpose": "user_data"},
            file_field_name="file",
            file_name=file_name,
            file_bytes=file_bytes,
            file_content_type=content_type,
        )
        self._trace_call(
            call_chain,
            stage="file_upload",
            event="sent",
            status="ok",
            message="openai source file upload request sent",
            details={"fileName": file_name, "byteSize": len(file_bytes), "purpose": "user_data"},
        )
        request = urllib.request.Request(
            f"{api_base}/files",
            data=body,
            headers={
                "Content-Type": multipart_content_type,
                "Authorization": f"Bearer {api_key}",
            },
        )
        started_at = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
            raw_response = response.read()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        payload = self._parse_json_bytes(raw_response)
        file_id = str(payload.get("id") or "").strip()
        if not file_id:
            raise RuntimeError("openai file upload did not return file id")
        self._trace_call(
            call_chain,
            stage="file_upload",
            event="received",
            status="ok",
            message="openai source file uploaded",
            details={"fileId": file_id, "elapsedMs": elapsed_ms},
        )
        return file_id

    def _delete_openai_input_file(
        self,
        *,
        api_base: str,
        api_key: str,
        file_id: str,
        call_chain: list[dict[str, Any]],
    ) -> None:
        if not file_id:
            return
        request = urllib.request.Request(
            f"{api_base}/files/{urllib.parse.quote(file_id)}",
            headers={"Authorization": f"Bearer {api_key}"},
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds):
                pass
            self._trace_call(
                call_chain,
                stage="file_cleanup",
                event="deleted",
                status="ok",
                message="openai source file deleted",
                details={"fileId": file_id},
            )
        except Exception as exc:
            self._trace_call(
                call_chain,
                stage="file_cleanup",
                event="delete_failed",
                status="retry",
                message="openai source file delete failed",
                details={"fileId": file_id, "error": truncate_text(str(exc), 240) or str(exc)},
            )

    def _normalize_request(
        self,
        payload: Any,
        *,
        default_kind: Literal["image", "video"],
    ) -> GenerateTextMediaRequest:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")

        normalized = dict(payload)
        normalized["kind"] = default_kind
        if "textAnalysisModel" not in normalized:
            normalized["textAnalysisModel"] = (
                normalized.get("analysisModel")
                or normalized.get("text_model")
                or normalized.get("promptAnalysisModel")
            )
        if normalized.get("videoModel") and not normalized.get("providerModel"):
            normalized["providerModel"] = normalized["videoModel"]
        if normalized.get("providerModel") and not normalized.get("videoModel"):
            normalized["videoModel"] = normalized["providerModel"]
        if "minDurationSeconds" not in normalized:
            normalized["minDurationSeconds"] = (
                normalized.get("minVideoDurationSeconds")
                or normalized.get("minDuration")
            )
        if "maxDurationSeconds" not in normalized:
            normalized["maxDurationSeconds"] = (
                normalized.get("maxVideoDurationSeconds")
                or normalized.get("maxDuration")
            )
        if "providerModel" not in normalized:
            normalized["providerModel"] = (
                normalized.get("videoModel")
                or normalized.get("modelName")
                or normalized.get("provider_model")
            )

        version_raw = normalized.get("version", 1)
        version_int = 1
        if isinstance(version_raw, int):
            version_int = version_raw
        elif isinstance(version_raw, str):
            candidate = version_raw.strip().lower()
            if candidate.startswith("v"):
                candidate = candidate[1:]
            if candidate.isdigit():
                version_int = int(candidate)
        version_int = min(10, max(1, version_int))
        if _SchemaGenerateTextMediaRequest is None:
            normalized["version"] = f"v{version_int}"
        else:
            normalized["version"] = version_int

        video_size = str(normalized.get("videoSize", "") or "").strip().lower().replace("x", "*")
        width_missing = normalized.get("width") in {None, ""}
        height_missing = normalized.get("height") in {None, ""}
        if video_size and (width_missing or height_missing):
            try:
                width, height = self._parse_video_size(video_size)
                if width_missing:
                    normalized["width"] = width
                if height_missing:
                    normalized["height"] = height
            except Exception:
                pass
        width_missing = normalized.get("width") in {None, ""}
        height_missing = normalized.get("height") in {None, ""}
        if width_missing or height_missing:
            ratio = str(normalized.get("aspectRatio", "9:16")).strip()
            width, height = self._resolution_for_aspect_ratio(ratio)
            if width_missing:
                normalized["width"] = width
            if height_missing:
                normalized["height"] = height

        if default_kind == "image":
            normalized.pop("durationSeconds", None)
            normalized.pop("minDurationSeconds", None)
            normalized.pop("maxDurationSeconds", None)
        elif normalized.get("durationSeconds") in {None, ""}:
            normalized["durationSeconds"] = 4.0

        extras = normalized.get("extras")
        if not isinstance(extras, dict):
            extras = {}
        style_preset = str(normalized.get("stylePreset", "") or "").strip()
        if style_preset and not str(extras.get("styleHint", "") or "").strip():
            extras["styleHint"] = style_preset
        normalized["extras"] = extras

        if hasattr(GenerateTextMediaRequest, "model_validate"):
            return GenerateTextMediaRequest.model_validate(normalized)  # type: ignore[attr-defined]
        return GenerateTextMediaRequest(**normalized)

    def _normalize_script_request(self, payload: Any) -> GenerateTextScriptRequest:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
        normalized = dict(payload)
        if "textAnalysisModel" not in normalized:
            normalized["textAnalysisModel"] = (
                normalized.get("analysisModel")
                or normalized.get("text_model")
                or normalized.get("textModel")
                or normalized.get("model")
                or normalized.get("modelName")
            )
        if hasattr(GenerateTextScriptRequest, "model_validate"):
            return GenerateTextScriptRequest.model_validate(normalized)  # type: ignore[attr-defined]
        return GenerateTextScriptRequest(**normalized)

    def _normalize_text_analysis_probe_request(self, payload: Any) -> ProbeTextAnalysisModelRequest:
        if isinstance(payload, ProbeTextAnalysisModelRequest):
            return payload
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        if isinstance(payload, str):
            normalized: dict[str, Any] = {"textAnalysisModel": payload}
        elif isinstance(payload, dict):
            normalized = dict(payload)
        elif payload is None:
            normalized = {}
        else:
            raise ValueError("payload must be a JSON object")
        if "textAnalysisModel" not in normalized:
            normalized["textAnalysisModel"] = (
                normalized.get("analysisModel")
                or normalized.get("text_model")
                or normalized.get("textModel")
                or normalized.get("model")
                or normalized.get("modelName")
            )
        if hasattr(ProbeTextAnalysisModelRequest, "model_validate"):
            return ProbeTextAnalysisModelRequest.model_validate(normalized)  # type: ignore[attr-defined]
        return ProbeTextAnalysisModelRequest(**normalized)

    def _call_text_analysis_model(
        self,
        *,
        text: str,
        purpose: str,
        selected_model: str | None,
        call_chain: list[dict[str, Any]],
        max_tokens: int,
    ) -> tuple[str, _TextAnalysisModelProfile, str]:
        requested_model = str(selected_model or "").strip() or None
        profile = self._resolve_text_analysis_model(requested_model)
        target = resolve_text_analysis_target(self.settings.model, requested_model or profile.key)
        profile = _text_analysis_model_profile(target.model_name)
        endpoint = str(target.endpoint or "").strip()
        api_key = str(target.api_key or "").strip()
        if not endpoint or not api_key:
            raise RuntimeError(f"text analysis provider is not configured for {target.model_name}")
        use_responses_api = should_use_responses_api(
            provider=target.provider,
            endpoint=endpoint,
            model_name=target.model_name,
        )
        request_endpoint = resolve_llm_request_endpoint(endpoint, use_responses_api=use_responses_api)
        body = build_text_request_body(
            model_name=target.model_name,
            system_prompt=self.settings.prompts.text_analysis_rewriter,
            user_prompt=text,
            temperature=min(0.45, max(0.08, self.settings.model.temperature)),
            max_tokens=min(max_tokens, self.settings.model.max_tokens),
            use_responses_api=use_responses_api,
            enable_thinking=looks_like_qwen_model(target.model_name),
        )
        request = urllib.request.Request(
            request_endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        self._trace_call(
            call_chain,
            stage="text_analysis",
            event="sent",
            status="ok",
            message=f"{purpose} text analysis request sent",
            details={
                "modelName": target.model_name,
                "provider": target.provider,
                "mode": "responses_key" if use_responses_api else target.mode,
                "maxTokens": body.get("max_output_tokens", body.get("max_tokens")),
            },
        )
        started_at = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
        except Exception as exc:
            raise RuntimeError(f"text analysis request failed ({target.model_name}): {exc}") from exc
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        payload = self._parse_json_bytes(raw_response)
        content = self._extract_text_response(payload, raw_response.decode("utf-8", errors="ignore")).strip()
        if not content:
            raise RuntimeError(f"text analysis response is empty ({target.model_name})")
        endpoint_host = ""
        try:
            endpoint_host = urllib.parse.urlparse(request_endpoint).netloc or request_endpoint
        except Exception:
            endpoint_host = request_endpoint
        self._trace_call(
            call_chain,
            stage="text_analysis",
            event="received",
            status="ok",
            message=f"{purpose} text analysis response received",
            details={"modelName": target.model_name, "elapsedMs": elapsed_ms, "outputLength": len(content)},
        )
        return content, profile, endpoint_host

    def _analyze_generation_prompt(
        self,
        *,
        media_type: Literal["image", "video"],
        request_obj: GenerateTextMediaRequest,
        prompt: str,
        call_chain: list[dict[str, Any]],
    ) -> tuple[str, _TextAnalysisModelProfile | None, str]:
        selected_model = getattr(request_obj, "textAnalysisModel", None)
        try:
            analyzed_prompt, profile, endpoint_host = self._call_text_analysis_model(
                text=(
                    f"任务：为{media_type}生成整理提示词。\n"
                    "请提炼人物、对白、语境、剧情冲突、镜头动作、光线和环境信息，"
                    "将原始文本改写成更适合生成模型理解的中文提示词。\n"
                    f"原始文本：{prompt}"
                ),
                purpose=f"{media_type} prompt",
                selected_model=selected_model,
                call_chain=call_chain,
                max_tokens=1600,
            )
            return analyzed_prompt, profile, endpoint_host
        except Exception as exc:
            self._trace_call(
                call_chain,
                stage="text_analysis",
                event="fallback",
                status="retry",
                message="text analysis skipped, fallback to shaped prompt",
                details={"error": truncate_text(str(exc), 300) or str(exc)},
            )
            return prompt, None, ""

    def _generate_media(
        self,
        media_type: Literal["image", "video"],
        request_obj: GenerateTextMediaRequest,
    ) -> GenerateTextMediaResponse:
        call_chain: list[dict[str, Any]] = []
        profile = self._resolve_profile(getattr(request_obj, "version", "v1"))
        generation_id = new_id("gen")
        prompt = str(getattr(request_obj, "prompt", "")).strip()
        version = profile.version
        extras = getattr(request_obj, "extras", {}) or {}
        if not isinstance(extras, dict):
            extras = {}
        refined_prompt, text_analysis_profile, text_analysis_endpoint_host = self._analyze_generation_prompt(
            media_type=media_type,
            request_obj=request_obj,
            prompt=prompt,
            call_chain=call_chain,
        )
        shaped_prompt = self._shape_prompt(media_type, refined_prompt, profile, extras)
        self._trace_call(
            call_chain,
            stage="request",
            event="accepted",
            status="ok",
            message="generation request accepted",
            details={
                "generationId": generation_id,
                "kind": media_type,
                "strategyVersion": version,
                "width": int(getattr(request_obj, "width", 0) or 0),
                "height": int(getattr(request_obj, "height", 0) or 0),
                "durationSeconds": float(getattr(request_obj, "durationSeconds", 0.0) or 0.0),
                "minDurationSeconds": getattr(request_obj, "minDurationSeconds", None),
                "maxDurationSeconds": getattr(request_obj, "maxDurationSeconds", None),
                "textAnalysisModel": str(getattr(request_obj, "textAnalysisModel", "") or "").strip() or None,
            },
        )
        self._trace_call(
            call_chain,
            stage="prompt",
            event="shaped",
            status="ok",
            message="prompt shaped for generation",
            details={
                "strategyVersion": version,
                "strategyLabel": profile.name,
                "promptLength": len(prompt),
                "refinedPromptLength": len(refined_prompt),
                "shapedPromptLength": len(shaped_prompt),
            },
        )

        video_spec = self._resolve_video_model_spec(request_obj) if media_type == "video" else None
        if media_type == "video":
            if video_spec and video_spec.provider_kind == "seeddance":
                provider_endpoint = self._resolve_seeddance_endpoint()
                provider_api_key = self._resolve_seeddance_api_key()
            else:
                provider_endpoint = self._resolve_video_endpoint()
                provider_api_key = str(self.settings.model.api_key or "").strip()
        else:
            provider_endpoint = str(self.settings.model.endpoint).strip()
            provider_api_key = str(self.settings.model.api_key or "").strip()
        if not provider_endpoint or not provider_api_key:
            self._trace_call(
                call_chain,
                stage="provider",
                event="config",
                status="error",
                message="provider config missing",
            )
            raise RuntimeError(f"{media_type} generation provider is not configured")

        try:
            if media_type == "video":
                remote_result = self._generate_video_with_selected_model(
                    request_obj=request_obj,
                    profile=profile,
                    shaped_prompt=shaped_prompt,
                    generation_id=generation_id,
                    call_chain=call_chain,
                )
            else:
                remote_result = self._generate_remote_media(
                    media_type=media_type,
                    request_obj=request_obj,
                    profile=profile,
                    shaped_prompt=shaped_prompt,
                    generation_id=generation_id,
                    call_chain=call_chain,
                )
        except Exception as exc:
            self._trace_call(
                call_chain,
                stage="generation",
                event="completed",
                status="error",
                message="generation failed",
                details={"error": truncate_text(str(exc), 400) or str(exc)},
            )
            raise

        endpoint_host = ""
        if provider_endpoint:
            try:
                endpoint_host = urllib.parse.urlparse(provider_endpoint).netloc or provider_endpoint
            except Exception:
                endpoint_host = provider_endpoint

        self._trace_call(
            call_chain,
            stage="generation",
            event="completed",
            status="ok",
            message="generation succeeded",
            details={"mimeType": remote_result["mimeType"]},
        )
        strategy_version = int(version.lstrip("v") or "1")
        resolved_video_spec = self._resolve_video_model_spec(request_obj) if media_type == "video" else None
        remote_metadata = remote_result.get("metadata", {}) if isinstance(remote_result.get("metadata"), dict) else {}
        remote_model_info = remote_metadata.get("modelInfo", {}) if isinstance(remote_metadata.get("modelInfo"), dict) else {}
        model_name = str(
            remote_model_info.get("providerModel")
            or remote_metadata.get("providerModel")
            or (resolved_video_spec.name if resolved_video_spec is not None else self.settings.model.model_name)
        ).strip()
        provider_name = str(
            remote_model_info.get("provider")
            or remote_metadata.get("provider")
            or (self.infer_video_provider(model_name) if media_type == "video" else self.settings.model.provider)
        ).strip()
        task_endpoint_host = str(remote_model_info.get("taskEndpointHost") or "").strip()
        if media_type == "video" and not task_endpoint_host:
            try:
                if resolved_video_spec and resolved_video_spec.provider_kind == "seeddance":
                    task_endpoint_host = urllib.parse.urlparse(self._resolve_seeddance_task_endpoint()).netloc or ""
                else:
                    task_endpoint_host = urllib.parse.urlparse(self._resolve_video_task_endpoint()).netloc or ""
            except Exception:
                task_endpoint_host = ""
        return self._build_response(
            media_type=media_type,
            generation_id=generation_id,
            version=version,
            prompt=prompt,
            shaped_prompt=shaped_prompt,
            source=f"remote:{model_name}",
            request_obj=request_obj,
            output_path=remote_result["path"],
            mime_type=remote_result["mimeType"],
            metadata={
                "provider": provider_name,
                "remote": True,
                "profileName": profile.name,
                "stylePreset": getattr(request_obj, "stylePreset", None),
                "textAnalysisModel": text_analysis_profile.key if text_analysis_profile is not None else getattr(request_obj, "textAnalysisModel", None),
                "modelInfo": {
                    "provider": provider_name,
                    "modelName": model_name,
                    "providerModel": model_name if media_type == "video" else None,
                    "textAnalysisModel": text_analysis_profile.key if text_analysis_profile is not None else getattr(request_obj, "textAnalysisModel", None),
                    "textAnalysisProvider": text_analysis_profile.provider if text_analysis_profile is not None else None,
                    "textAnalysisEndpointHost": text_analysis_endpoint_host or None,
                    "endpointHost": endpoint_host,
                    "taskEndpointHost": task_endpoint_host or None,
                    "temperature": self.settings.model.temperature if media_type != "video" else None,
                    "maxTokens": self.settings.model.max_tokens if media_type != "video" else None,
                    "strategyVersion": strategy_version,
                    "strategyVersionLabel": profile.name,
                    "strategySummary": profile.summary,
                    "mediaKind": media_type,
                    "timeoutSeconds": (
                        self.settings.model.video_poll_timeout_seconds
                        if media_type == "video"
                        else self.settings.model.timeout_seconds
                    ),
                    "promptExtend": self.settings.model.video_prompt_extend if media_type == "video" else None,
                },
                "callChain": call_chain,
                **remote_result.get("metadata", {}),
            },
        )

    def _generate_script(
        self,
        request_obj: GenerateTextScriptRequest,
        *,
        source_text_file_path: Path | None = None,
        source_text_file_name: str | None = None,
    ) -> GenerateTextScriptResponse:
        call_chain: list[dict[str, Any]] = []
        generation_id = new_id("script")
        source_text = str(getattr(request_obj, "text", "")).strip()
        requested_visual_style = str(getattr(request_obj, "visualStyle", "") or "").strip()
        requested_text_analysis_model = str(getattr(request_obj, "textAnalysisModel", "") or "").strip()
        visual_style = requested_visual_style or _infer_script_visual_style(source_text)
        created_at = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

        self._trace_call(
            call_chain,
            stage="request",
            event="accepted",
            status="ok",
            message="script generation request accepted",
            details={
                "generationId": generation_id,
                "textLength": len(source_text),
                "visualStyle": visual_style,
                "textAnalysisModel": requested_text_analysis_model or self._default_text_analysis_model().key,
            },
        )

        text_analysis_profile = self._resolve_text_analysis_model(requested_text_analysis_model or None)
        text_analysis_target = resolve_text_analysis_target(
            self.settings.model,
            requested_text_analysis_model or text_analysis_profile.key,
        )
        endpoint = str(text_analysis_target.endpoint or "").strip()
        api_key = str(text_analysis_target.api_key or "").strip()
        fallback_used = False
        configured_fallback_name = str(
            self.settings.model.text_analysis_fallback_model_name
            or self.settings.model.model_name
            or ""
        ).strip()
        configured_fallback_profile = self._resolve_text_analysis_model(configured_fallback_name or None)
        configured_fallback_target = resolve_text_analysis_target(
            self.settings.model,
            configured_fallback_profile.key,
        )
        if not endpoint or not api_key:
            fallback_name = configured_fallback_name
            fallback_profile = configured_fallback_profile
            fallback_target = configured_fallback_target
            fallback_endpoint = str(fallback_target.endpoint or "").strip()
            fallback_api_key = str(fallback_target.api_key or "").strip()
            if (
                fallback_name
                and fallback_profile.key != text_analysis_profile.key
                and fallback_endpoint
                and fallback_api_key
            ):
                fallback_used = True
                self._trace_call(
                    call_chain,
                    stage="provider",
                    event="fallback",
                    status="retry",
                    message="text analysis model config missing, fallback to configured compatible model",
                    details={
                        "requestedModel": requested_text_analysis_model or text_analysis_profile.key,
                        "resolvedModel": fallback_target.model_name,
                        "provider": fallback_target.provider,
                    },
                )
                text_analysis_profile = fallback_profile
                text_analysis_target = fallback_target
                endpoint = fallback_endpoint
                api_key = fallback_api_key
        if not endpoint or not api_key:
            self._trace_call(
                call_chain,
                stage="provider",
                event="config",
                status="error",
                message="provider config missing",
                details={"requestedModel": requested_text_analysis_model or text_analysis_profile.key},
            )
            raise RuntimeError(
                f"text script provider is not configured for model '{requested_text_analysis_model or text_analysis_profile.key}'"
            )

        minimum_shot_count, recommended_shot_count = _estimate_script_shot_targets(source_text)
        inline_user_prompt = (
            "请基于下面的正文生成一份可直接用于短剧生产的 Markdown 脚本。\n"
            f"{'用户指定视觉风格：' + visual_style if requested_visual_style else '视觉风格：请你根据题材与情绪自动决策，并在全片保持统一。'}\n"
            f"分镜覆盖要求：必须覆盖原文主线与关键转折，至少输出 {minimum_shot_count} 个分镜，建议输出 {recommended_shot_count} 个分镜。\n"
            "对话还原要求：尽量还原小说中的全部人物对话，优先保留原文原句，不要改写成摘要。\n"
            "分镜细节要求：每个分镜都要写清剧情节点、人物动作、情绪变化、镜头运动与环境细节。\n"
            "剧情顺序要求：必须按原文叙事顺序逐段覆盖，不得跳段合并或忽略关键情节。\n"
            "连续性要求：前后分镜内容必须连贯，中间连接点必须自然过渡。\n"
            "声音要求：禁止上一镜声音戛然而止后下一镜声音立刻硬切出现；应使用尾音延续、环境音桥接、渐入渐出或 J-cut/L-cut 处理。\n"
            "时长要求：每个分镜的“建议时长”必须写区间（如 3-5 秒），不要只写单点秒数。\n"
            "若原文篇幅较长，请保证开端、发展、转折、高潮、结局都有镜头覆盖，避免只写前几段情节。\n"
            "若输出长度受限，请优先保留关键对白与剧情推进信息，再压缩修饰性描写，不得省略关键台词。\n"
            "如果原文信息不完整，请在不偏离原意的前提下补足角色外观锚点、环境视觉基调和分镜动作。\n"
            "请直接输出最终剧本，不要写解释、前言或额外说明。\n\n"
            "【用户正文开始】\n"
            f"{source_text}\n"
            "【用户正文结束】"
        )
        attached_file_prompt = (
            "请基于我附带的 TXT 正文文件生成一份可直接用于短剧生产的 Markdown 脚本。\n"
            f"{'用户指定视觉风格：' + visual_style if requested_visual_style else '视觉风格：请你根据题材与情绪自动决策，并在全片保持统一。'}\n"
            f"分镜覆盖要求：必须覆盖原文主线与关键转折，至少输出 {minimum_shot_count} 个分镜，建议输出 {recommended_shot_count} 个分镜。\n"
            "对话还原要求：尽量还原小说中的全部人物对话，优先保留原文原句，不要改写成摘要。\n"
            "分镜细节要求：每个分镜都要写清剧情节点、人物动作、情绪变化、镜头运动与环境细节。\n"
            "剧情顺序要求：必须按原文叙事顺序逐段覆盖，不得跳段合并或忽略关键情节。\n"
            "连续性要求：前后分镜内容必须连贯，中间连接点必须自然过渡。\n"
            "声音要求：禁止上一镜声音戛然而止后下一镜声音立刻硬切出现；应使用尾音延续、环境音桥接、渐入渐出或 J-cut/L-cut 处理。\n"
            "时长要求：每个分镜的“建议时长”必须写区间（如 3-5 秒），不要只写单点秒数。\n"
            "若原文篇幅较长，请保证开端、发展、转折、高潮、结局都有镜头覆盖，避免只写前几段情节。\n"
            "若输出长度受限，请优先保留关键对白与剧情推进信息，再压缩修饰性描写，不得省略关键台词。\n"
            "如果原文信息不完整，请在不偏离原意的前提下补足角色外观锚点、环境视觉基调和分镜动作。\n"
            "请完整阅读附件文件内容，并直接输出最终剧本，不要写解释、前言或额外说明。"
        )
        temperature = min(0.45, max(0.12, self.settings.model.temperature + 0.05))
        script_token_candidates = _script_output_token_candidates(self.settings.model.max_tokens)
        max_output_tokens = script_token_candidates[0]
        use_openai_file_input = (
            source_text_file_path is not None
            and self._is_openai_text_analysis_target(provider=text_analysis_target.provider, endpoint=endpoint)
        )
        input_mode = "inline"
        raw_response = b""
        script_request_timeout_seconds = max(float(self.settings.model.timeout_seconds), 300.0)

        def send_inline_script_request(
            *,
            target_endpoint: str,
            target_api_key: str,
            target_model_name: str,
            target_provider: str,
            target_mode: str,
            fallback_flag: bool,
            max_tokens: int,
        ) -> bytes:
            use_responses_api = should_use_responses_api(
                provider=target_provider,
                endpoint=target_endpoint,
                model_name=target_model_name,
            )
            request_endpoint = resolve_llm_request_endpoint(target_endpoint, use_responses_api=use_responses_api)
            body = build_text_request_body(
                model_name=target_model_name,
                system_prompt=self.settings.prompts.short_drama_script,
                user_prompt=inline_user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                use_responses_api=use_responses_api,
                enable_thinking=False,
            )
            request = urllib.request.Request(
                request_endpoint,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {target_api_key}",
                },
            )
            self._trace_call(
                call_chain,
                stage="remote_request",
                event="sent",
                status="ok",
                message="remote script generation request sent",
                details={
                    "requestedModel": requested_text_analysis_model or text_analysis_profile.key,
                    "modelName": target_model_name,
                    "provider": target_provider,
                    "mode": "responses_key" if use_responses_api else target_mode,
                    "fallbackUsed": fallback_flag,
                    "temperature": body["temperature"],
                    "maxTokens": body.get("max_output_tokens", body.get("max_tokens")),
                },
            )

            request_started = time.perf_counter()
            with urllib.request.urlopen(request, timeout=script_request_timeout_seconds) as response:
                response_bytes = response.read()
            elapsed_ms = int((time.perf_counter() - request_started) * 1000)
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="ok",
                message="remote script generation response received",
                details={
                    "byteSize": len(response_bytes),
                    "elapsedMs": elapsed_ms,
                },
            )
            return response_bytes

        def read_http_error_body(exc: urllib.error.HTTPError) -> str:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                body_text = ""
            return body_text

        def should_retry_with_lower_tokens(status_code: int, body_text: str) -> bool:
            if status_code not in {400, 413, 422}:
                return False
            normalized = body_text.lower()
            if not normalized:
                return True
            return any(
                keyword in normalized
                for keyword in (
                    "max_output_tokens",
                    "max_tokens",
                    "context length",
                    "context_window",
                    "token",
                    "too long",
                    "too many",
                )
            )

        def request_inline_with_token_fallback(
            *,
            target_endpoint: str,
            target_api_key: str,
            target_model_name: str,
            target_provider: str,
            target_mode: str,
            fallback_flag: bool,
        ) -> tuple[bytes, int]:
            for index, token_limit in enumerate(script_token_candidates):
                try:
                    response_bytes = send_inline_script_request(
                        target_endpoint=target_endpoint,
                        target_api_key=target_api_key,
                        target_model_name=target_model_name,
                        target_provider=target_provider,
                        target_mode=target_mode,
                        fallback_flag=fallback_flag,
                        max_tokens=token_limit,
                    )
                    return response_bytes, token_limit
                except urllib.error.HTTPError as exc:
                    status_code = int(exc.code)
                    body_text = read_http_error_body(exc)
                    can_retry_with_lower_tokens = (
                        index < len(script_token_candidates) - 1
                        and should_retry_with_lower_tokens(status_code, body_text)
                    )
                    if not can_retry_with_lower_tokens:
                        raise
                    self._trace_call(
                        call_chain,
                        stage="remote_request",
                        event="retry",
                        status="retry",
                        message="script request token budget rejected, retrying with lower max tokens",
                        details={
                            "statusCode": status_code,
                            "modelName": target_model_name,
                            "provider": target_provider,
                            "previousMaxTokens": token_limit,
                            "nextMaxTokens": script_token_candidates[index + 1],
                        },
                    )
            raise RuntimeError("script request token fallback exhausted")

        if use_openai_file_input:
            api_base = self._openai_api_base(endpoint)
            uploaded_file_id = ""
            try:
                uploaded_file_id = self._upload_openai_input_file(
                    api_base=api_base,
                    api_key=api_key,
                    source_text_file_path=source_text_file_path,
                    source_text_file_name=source_text_file_name,
                    call_chain=call_chain,
                )
                file_body = {
                    "model": text_analysis_target.model_name,
                    "input": [
                        {
                            "role": "system",
                            "content": [{"type": "input_text", "text": self.settings.prompts.short_drama_script}],
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": attached_file_prompt},
                                {"type": "input_file", "file_id": uploaded_file_id},
                            ],
                        },
                    ],
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
                request = urllib.request.Request(
                    f"{api_base}/responses",
                    data=json.dumps(file_body, ensure_ascii=False).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                self._trace_call(
                    call_chain,
                    stage="remote_request",
                    event="sent",
                    status="ok",
                    message="remote script generation request sent with file input",
                    details={
                        "requestedModel": requested_text_analysis_model or text_analysis_profile.key,
                        "modelName": text_analysis_target.model_name,
                        "provider": text_analysis_target.provider,
                        "mode": "responses_file_input",
                        "fallbackUsed": fallback_used,
                        "temperature": temperature,
                        "maxOutputTokens": max_output_tokens,
                        "fileName": source_text_file_name or source_text_file_path.name,
                    },
                )
                request_started = time.perf_counter()
                with urllib.request.urlopen(request, timeout=script_request_timeout_seconds) as response:
                    raw_response = response.read()
                elapsed_ms = int((time.perf_counter() - request_started) * 1000)
                self._trace_call(
                    call_chain,
                    stage="remote_response",
                    event="received",
                    status="ok",
                    message="remote script generation response received",
                    details={
                        "byteSize": len(raw_response),
                        "elapsedMs": elapsed_ms,
                    },
                )
                input_mode = "file"
            except Exception as exc:
                self._trace_call(
                    call_chain,
                    stage="remote_request",
                    event="fallback",
                    status="retry",
                    message="file input request failed, fallback to inline text request",
                    details={"error": truncate_text(str(exc), 320) or str(exc)},
                )
            finally:
                self._delete_openai_input_file(
                    api_base=api_base,
                    api_key=api_key,
                    file_id=uploaded_file_id,
                    call_chain=call_chain,
                )

        if not raw_response:
            try:
                raw_response, max_output_tokens = request_inline_with_token_fallback(
                    target_endpoint=endpoint,
                    target_api_key=api_key,
                    target_model_name=text_analysis_target.model_name,
                    target_provider=text_analysis_target.provider,
                    target_mode=text_analysis_target.mode,
                    fallback_flag=fallback_used,
                )
            except (TimeoutError, socket.timeout) as exc:
                self._trace_call(
                    call_chain,
                    stage="remote_response",
                    event="received",
                    status="error",
                    message="remote script generation timeout",
                    details={"error": str(exc)},
                )
                raise RuntimeError(f"remote script generation timeout: {exc}") from exc
            except urllib.error.HTTPError as exc:
                status_code = int(exc.code)
                fallback_endpoint = str(configured_fallback_target.endpoint or "").strip()
                fallback_api_key = str(configured_fallback_target.api_key or "").strip()
                can_retry_with_fallback = (
                    status_code in {401, 403, 404}
                    and configured_fallback_name
                    and configured_fallback_profile.key != text_analysis_profile.key
                    and configured_fallback_target.model_name != text_analysis_target.model_name
                    and fallback_endpoint
                    and fallback_api_key
                )
                if can_retry_with_fallback:
                    self._trace_call(
                        call_chain,
                        stage="provider",
                        event="fallback",
                        status="retry",
                        message="primary text analysis model rejected, fallback to configured compatible model",
                        details={
                            "statusCode": status_code,
                            "requestedModel": requested_text_analysis_model or text_analysis_profile.key,
                            "resolvedModel": configured_fallback_target.model_name,
                            "provider": configured_fallback_target.provider,
                        },
                    )
                    text_analysis_profile = configured_fallback_profile
                    text_analysis_target = configured_fallback_target
                    endpoint = fallback_endpoint
                    api_key = fallback_api_key
                    fallback_used = True
                    try:
                        raw_response, max_output_tokens = request_inline_with_token_fallback(
                            target_endpoint=endpoint,
                            target_api_key=api_key,
                            target_model_name=text_analysis_target.model_name,
                            target_provider=text_analysis_target.provider,
                            target_mode=text_analysis_target.mode,
                            fallback_flag=True,
                        )
                    except (TimeoutError, socket.timeout) as retry_exc:
                        self._trace_call(
                            call_chain,
                            stage="remote_response",
                            event="received",
                            status="error",
                            message="remote script generation timeout",
                            details={"error": str(retry_exc)},
                        )
                        raise RuntimeError(f"remote script generation timeout: {retry_exc}") from retry_exc
                    except urllib.error.HTTPError as retry_exc:
                        self._trace_call(
                            call_chain,
                            stage="remote_response",
                            event="received",
                            status="error",
                            message="remote script generation http error",
                            details={"statusCode": int(retry_exc.code)},
                        )
                        raise RuntimeError(f"remote script generation http error: {retry_exc.code}") from retry_exc
                    except urllib.error.URLError as retry_exc:
                        self._trace_call(
                            call_chain,
                            stage="remote_response",
                            event="received",
                            status="error",
                            message="remote script generation network error",
                            details={"error": str(retry_exc)},
                        )
                        raise RuntimeError(f"remote script generation network error: {retry_exc}") from retry_exc
                else:
                    self._trace_call(
                        call_chain,
                        stage="remote_response",
                        event="received",
                        status="error",
                        message="remote script generation http error",
                        details={"statusCode": status_code},
                    )
                    raise RuntimeError(f"remote script generation http error: {status_code}") from exc
            except urllib.error.URLError as exc:
                self._trace_call(
                    call_chain,
                    stage="remote_response",
                    event="received",
                    status="error",
                    message="remote script generation network error",
                    details={"error": str(exc)},
                )
                raise RuntimeError(f"remote script generation network error: {exc}") from exc

        payload = self._parse_json_bytes(raw_response)
        script_markdown = self._extract_text_response(payload, raw_response.decode("utf-8", errors="ignore"))
        if not script_markdown:
            self._trace_call(
                call_chain,
                stage="response_extract",
                event="text",
                status="error",
                message="script response content is empty",
            )
            raise RuntimeError("script generation response is empty")

        self._trace_call(
            call_chain,
            stage="response_extract",
            event="text",
            status="ok",
            message="script markdown extracted",
            details={"outputLength": len(script_markdown)},
        )

        endpoint_host = ""
        try:
            endpoint_host = urllib.parse.urlparse(endpoint).netloc or endpoint
        except Exception:
            endpoint_host = endpoint

        date_label = datetime.utcnow().strftime("%Y%m%d")
        output_dir = self.storage.outputs_root / "text_generation" / date_label
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{generation_id}_script.md"
        markdown_path.write_text(script_markdown, encoding="utf-8")
        relative_markdown_path = markdown_path.resolve().relative_to(self.storage.root.resolve()).as_posix()
        markdown_url = self.storage.build_public_url(relative_markdown_path)

        return self._build_model(
            GenerateTextScriptResponse,
            {
                "id": generation_id,
                "sourceText": source_text,
                "visualStyle": visual_style,
                "outputFormat": "markdown",
                "scriptMarkdown": script_markdown,
                "markdownFilePath": relative_markdown_path,
                "markdownFileUrl": markdown_url,
                "downloadUrl": markdown_url,
                "source": f"remote:{text_analysis_target.model_name}",
                "createdAt": created_at,
                "modelInfo": {
                    "provider": text_analysis_target.provider,
                    "modelName": text_analysis_target.model_name,
                    "requestedModel": requested_text_analysis_model or text_analysis_profile.key,
                    "resolvedModel": text_analysis_target.model_name,
                    "textAnalysisModel": requested_text_analysis_model or text_analysis_profile.key,
                    "selectedTextAnalysisModel": text_analysis_profile.key,
                    "endpointHost": endpoint_host,
                    "temperature": temperature,
                    "maxTokens": max_output_tokens,
                    "timeoutSeconds": self.settings.model.timeout_seconds,
                    "fallbackUsed": fallback_used,
                    "inputMode": input_mode,
                },
                "callChain": call_chain,
                "metadata": {
                    "systemPromptName": "ai-short-drama-script-expert",
                    "visualStyle": visual_style,
                    "textAnalysisModel": requested_text_analysis_model or text_analysis_profile.key,
                    "requestedTextAnalysisModel": requested_text_analysis_model or text_analysis_profile.key,
                    "resolvedTextAnalysisModel": text_analysis_target.model_name,
                    "fallbackUsed": fallback_used,
                    "sourceTextLength": len(source_text),
                    "outputFormat": "markdown",
                    "markdownFilePath": relative_markdown_path,
                    "markdownFileUrl": markdown_url,
                    "inputMode": input_mode,
                    "rawTopLevelKeys": list(payload.keys())[:12],
                },
            },
        )

    def _generate_video_with_selected_model(
        self,
        *,
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        spec = self._resolve_video_model_spec(request_obj)
        if spec.provider_kind == "seeddance":
            return self._generate_seeddance_video(
                request_obj=request_obj,
                profile=profile,
                shaped_prompt=shaped_prompt,
                generation_id=generation_id,
                call_chain=call_chain,
            )
        if spec.provider_kind == "qwen_vl_workflow":
            if hasattr(request_obj, "model_copy"):
                backend_request = request_obj.model_copy(deep=True)  # type: ignore[attr-defined]
            else:
                payload = request_obj.model_dump() if hasattr(request_obj, "model_dump") else dict(request_obj.__dict__)
                backend_request = GenerateTextMediaRequest(**payload)
            backend_model_name = (spec.backend_model_name or self.settings.model.video_model_name or "wan2.6-t2v").strip()
            backend_request.providerModel = backend_model_name
            backend_request.videoModel = backend_model_name
            rewritten_prompt = self._rewrite_prompt_with_qwen_vl(
                shaped_prompt=shaped_prompt,
                call_chain=call_chain,
            )
            result = self._generate_dashscope_video(
                request_obj=backend_request,
                profile=profile,
                shaped_prompt=rewritten_prompt,
                generation_id=generation_id,
                call_chain=call_chain,
            )
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            metadata["provider"] = "aliyun-bailian"
            metadata["selectedProviderModel"] = spec.name
            metadata["providerModel"] = spec.name
            metadata["actualProviderModel"] = backend_model_name
            metadata["resolvedBackendModel"] = backend_model_name
            model_info = metadata.get("modelInfo") if isinstance(metadata.get("modelInfo"), dict) else {}
            model_info["provider"] = "aliyun-bailian"
            model_info["modelName"] = backend_model_name
            model_info["providerModel"] = spec.name
            model_info["actualModelName"] = backend_model_name
            model_info["resolvedBackendModel"] = backend_model_name
            metadata["modelInfo"] = model_info
            result["metadata"] = metadata
            return result
        return self._generate_dashscope_video(
            request_obj=request_obj,
            profile=profile,
            shaped_prompt=shaped_prompt,
            generation_id=generation_id,
            call_chain=call_chain,
        )

    def _generate_remote_media(
        self,
        *,
        media_type: Literal["image", "video"],
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if media_type == "video":
            return self._generate_dashscope_video(
                request_obj=request_obj,
                profile=profile,
                shaped_prompt=shaped_prompt,
                generation_id=generation_id,
                call_chain=call_chain,
            )

        width, height = self._resolve_dimensions(request_obj)
        duration_seconds = float(getattr(request_obj, "durationSeconds", 0.0) or 0.0)
        aspect_ratio = self._aspect_ratio_label(width, height)
        request_model_name = str(self.settings.model.image_model_name or self.settings.model.model_name or "").strip()
        extras = getattr(request_obj, "extras", None)
        force_provider_model_for_image = bool(isinstance(extras, dict) and extras.get("forceProviderModelForImage"))
        if media_type == "image" and force_provider_model_for_image:
            requested_provider_model = str(getattr(request_obj, "providerModel", "") or "").strip()
            if requested_provider_model:
                normalized_provider_model = _normalize_video_model_name(requested_provider_model)
                spec = _VIDEO_MODELS.get(normalized_provider_model) if normalized_provider_model else None
                if spec is not None:
                    request_model_name = (spec.backend_model_name or spec.name).strip() or request_model_name
                else:
                    request_model_name = requested_provider_model
        if _looks_like_seedream_image_model(request_model_name):
            return self._generate_seedream_image(
                request_obj=request_obj,
                shaped_prompt=shaped_prompt,
                generation_id=generation_id,
                call_chain=call_chain,
                request_model_name=request_model_name,
            )

        endpoint = str(self.settings.model.endpoint).strip()
        if not endpoint:
            raise RuntimeError("model endpoint is empty")
        if not self.settings.model.api_key:
            raise RuntimeError("model api_key is empty")

        use_responses_api = should_use_responses_api(
            provider=self.settings.model.provider,
            endpoint=endpoint,
            model_name=request_model_name,
        )
        request_endpoint = resolve_llm_request_endpoint(endpoint, use_responses_api=use_responses_api)
        body = build_text_request_body(
            model_name=request_model_name,
            system_prompt=self.settings.prompts.generation_json_only,
            user_prompt=(
                f"Task: generate {media_type} from text.\n"
                f"Aspect ratio: {aspect_ratio}\n"
                f"Resolution: {width}x{height}\n"
                f"Duration seconds: {duration_seconds:.2f}\n"
                f"Prompt: {shaped_prompt}\n"
                'Output JSON: {"file_url":"https://...", "base64_data":"...", "mime_type":"image/png or video/mp4"}'
            ),
            temperature=min(0.35, max(0.05, self.settings.model.temperature)),
            max_tokens=min(900, self.settings.model.max_tokens),
            use_responses_api=use_responses_api,
            enable_thinking=looks_like_qwen_model(request_model_name),
        )

        request = urllib.request.Request(
            request_endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.model.api_key}",
            },
        )
        self._trace_call(
            call_chain,
            stage="remote_request",
            event="sent",
            status="ok",
            message="remote generation request sent",
            details={
                "modelName": request_model_name,
                "provider": self.settings.model.provider,
                "kind": media_type,
                "temperature": body["temperature"],
                "maxTokens": body.get("max_output_tokens", body.get("max_tokens")),
            },
        )
        request_started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
            elapsed_ms = int((time.perf_counter() - request_started) * 1000)
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="ok",
                message="remote generation response received",
                details={
                    "byteSize": len(raw_response),
                    "elapsedMs": elapsed_ms,
                },
            )
        except (TimeoutError, socket.timeout) as exc:
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="error",
                message="remote generation timeout",
                details={"error": str(exc)},
            )
            raise RuntimeError(f"remote {media_type} generation timeout: {exc}") from exc
        except urllib.error.HTTPError as exc:
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="error",
                message="remote generation http error",
                details={"statusCode": int(exc.code)},
            )
            raise RuntimeError(f"remote {media_type} generation http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="error",
                message="remote generation network error",
                details={"error": str(exc)},
            )
            raise RuntimeError(f"remote {media_type} generation network error: {exc}") from exc

        payload = self._parse_json_bytes(raw_response)
        self._trace_call(
            call_chain,
            stage="remote_payload",
            event="parsed",
            status="ok",
            message="remote payload parsed",
            details={"topLevelKeys": list(payload.keys())[:12]},
        )
        media_blob = self._extract_media_blob(
            media_type=media_type,
            payload=payload,
            raw_text=raw_response.decode("utf-8", errors="ignore"),
            call_chain=call_chain,
        )
        if media_blob is None:
            raise RuntimeError("remote response did not include usable media data")

        mime_type = media_blob["mimeType"] or ("image/png" if media_type == "image" else "video/mp4")
        extension = self._extension_from_mime_or_url(mime_type, media_blob.get("sourceUrl"), media_type)
        output_path = self._prepare_output_path(generation_id, media_type, extension)
        output_path.write_bytes(media_blob["data"])
        self._trace_call(
            call_chain,
            stage="output",
            event="saved",
            status="ok",
            message="generated media file saved",
            details={
                "filePath": output_path.as_posix(),
                "mimeType": mime_type,
                "byteSize": output_path.stat().st_size,
            },
        )
        return {
            "path": output_path,
            "mimeType": mime_type,
            "metadata": {
                "remoteSourceUrl": media_blob.get("sourceUrl", ""),
                "byteSize": output_path.stat().st_size,
                "aspectRatio": aspect_ratio,
                "resolution": f"{width}x{height}",
            },
        }

    def _generate_seedream_image(
        self,
        *,
        request_obj: GenerateTextMediaRequest,
        shaped_prompt: str,
        generation_id: str,
        call_chain: list[dict[str, Any]],
        request_model_name: str,
    ) -> dict[str, Any]:
        endpoint = self._resolve_seedream_image_endpoint()
        api_key = self._resolve_seedream_api_key()
        if not endpoint:
            raise RuntimeError("seedream image endpoint is empty")
        if not api_key:
            raise RuntimeError("seedream api key is empty")

        width, height = self._resolve_dimensions(request_obj)
        aspect_ratio = self._aspect_ratio_label(width, height)
        extras = getattr(request_obj, "extras", None)
        if not isinstance(extras, dict):
            extras = {}

        requested_provider_model = str(getattr(request_obj, "providerModel", "") or "").strip()
        model_name = _normalize_seedream_image_model_name(requested_provider_model or request_model_name)
        response_format = str(extras.get("response_format") or extras.get("responseFormat") or "url").strip().lower()
        if response_format not in {"url", "b64_json"}:
            response_format = "url"
        sequential_mode = str(
            extras.get("sequential_image_generation")
            or extras.get("sequentialImageGeneration")
            or "disabled"
        ).strip().lower()
        if sequential_mode not in {"enabled", "disabled", "auto"}:
            sequential_mode = "disabled"
        stream = self._coerce_extra_bool(extras.get("stream"), default=False)
        watermark = self._coerce_extra_bool(extras.get("watermark"), default=True)
        size = self._resolve_seedream_image_size(width=width, height=height, extras=extras)

        body: dict[str, Any] = {
            "model": model_name,
            "prompt": shaped_prompt,
            "sequential_image_generation": sequential_mode,
            "response_format": response_format,
            "size": size,
            "stream": stream,
            "watermark": watermark,
        }

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-Api-Key": api_key,
            },
        )
        self._trace_call(
            call_chain,
            stage="remote_request",
            event="sent",
            status="ok",
            message="seedream image request sent",
            details={
                "modelName": model_name,
                "provider": "volcengine",
                "size": size,
                "responseFormat": response_format,
                "watermark": watermark,
                "stream": stream,
            },
        )
        request_started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
            elapsed_ms = int((time.perf_counter() - request_started) * 1000)
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="ok",
                message="seedream image response received",
                details={
                    "byteSize": len(raw_response),
                    "elapsedMs": elapsed_ms,
                },
            )
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"seedream image generation timeout: {exc}") from exc
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            detail_text = truncate_text(detail.strip(), 240)
            if detail_text:
                raise RuntimeError(f"seedream image generation http error: {exc.code} {detail_text}") from exc
            raise RuntimeError(f"seedream image generation http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"seedream image generation network error: {exc}") from exc

        payload = self._parse_json_bytes(raw_response)
        self._trace_call(
            call_chain,
            stage="remote_payload",
            event="parsed",
            status="ok",
            message="seedream image payload parsed",
            details={"topLevelKeys": list(payload.keys())[:12]},
        )
        media_blob = self._extract_media_blob(
            media_type="image",
            payload=payload,
            raw_text=raw_response.decode("utf-8", errors="ignore"),
            call_chain=call_chain,
        )
        if media_blob is None:
            raise RuntimeError("seedream response did not include usable image data")

        mime_type = media_blob["mimeType"] or "image/png"
        extension = self._extension_from_mime_or_url(mime_type, media_blob.get("sourceUrl"), "image")
        output_path = self._prepare_output_path(generation_id, "image", extension)
        output_path.write_bytes(media_blob["data"])
        self._trace_call(
            call_chain,
            stage="output",
            event="saved",
            status="ok",
            message="seedream image file saved",
            details={
                "filePath": output_path.as_posix(),
                "mimeType": mime_type,
                "byteSize": output_path.stat().st_size,
            },
        )
        return {
            "path": output_path,
            "mimeType": mime_type,
            "metadata": {
                "remoteSourceUrl": media_blob.get("sourceUrl", ""),
                "byteSize": output_path.stat().st_size,
                "aspectRatio": aspect_ratio,
                "resolution": f"{width}x{height}",
                "provider": "volcengine",
                "providerModel": model_name,
                "requestedSize": size,
                "modelInfo": {
                    "provider": "volcengine",
                    "modelName": model_name,
                    "providerModel": model_name,
                    "endpointHost": urllib.parse.urlparse(endpoint).netloc or endpoint,
                    "mediaKind": "image",
                },
            },
        }

    def _resolve_seedream_image_size(self, *, width: int, height: int, extras: dict[str, Any]) -> str:
        raw = str(
            extras.get("size")
            or extras.get("imageSizeTier")
            or extras.get("seedreamSize")
            or ""
        ).strip().upper()
        if raw in {"1K", "2K", "4K"}:
            return raw
        longest_edge = max(width, height)
        if longest_edge > 1024:
            return "2K"
        return "1K"

    def _rewrite_prompt_with_qwen_vl(self, *, shaped_prompt: str, call_chain: list[dict[str, Any]]) -> str:
        endpoint = str(self.settings.model.endpoint or "").strip()
        if not endpoint or not self.settings.model.api_key:
            return shaped_prompt
        model_name = str(self.settings.model.vision_model_name or "qwen-vl-plus-latest").strip()
        if not model_name:
            model_name = "qwen-vl-plus-latest"
        body = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self.settings.prompts.qwen_vl_prompt_rewriter,
                },
                {
                    "role": "user",
                    "content": shaped_prompt,
                },
            ],
            "temperature": min(0.4, max(0.05, self.settings.model.temperature)),
            "max_tokens": min(1200, self.settings.model.max_tokens),
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.model.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
        except Exception as exc:
            self._trace_call(
                call_chain,
                stage="prompt",
                event="qwen_vl_rewrite",
                status="retry",
                message="qwen-vl rewrite failed, fallback to original prompt",
                details={"error": truncate_text(str(exc), 300) or str(exc)},
            )
            return shaped_prompt
        payload = self._parse_json_bytes(raw_response)
        rewritten = self._extract_text_response(payload, raw_response.decode("utf-8", errors="ignore")).strip()
        if not rewritten:
            return shaped_prompt
        rewritten = self._enforce_video_hard_requirements(rewritten)
        self._trace_call(
            call_chain,
            stage="prompt",
            event="qwen_vl_rewrite",
            status="ok",
            message="prompt rewritten by qwen-vl workflow",
            details={"rawLength": len(shaped_prompt), "rewrittenLength": len(rewritten)},
        )
        return rewritten

    def _generate_seeddance_video(
        self,
        *,
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        endpoint = self._resolve_seeddance_endpoint()
        task_endpoint = self._resolve_seeddance_task_endpoint()
        api_key = self._resolve_seeddance_api_key()
        if not endpoint:
            raise RuntimeError("seeddance video endpoint is empty")
        if not task_endpoint:
            raise RuntimeError("seeddance video task endpoint is empty")
        if not api_key:
            raise RuntimeError("seeddance api key is empty")

        spec = self._resolve_video_model_spec(request_obj)
        width, height = self._resolve_dimensions(request_obj)
        normalized_width, normalized_height, normalized_size = self._normalize_video_size(
            spec=spec,
            width=width,
            height=height,
        )
        requested_duration, min_requested_duration, max_requested_duration = self._resolve_requested_video_duration_bounds(request_obj)
        normalized_duration = self._normalize_video_duration(
            spec=spec,
            requested=requested_duration,
            min_requested=min_requested_duration,
            max_requested=max_requested_duration,
        )
        reference_image_url = self._resolve_seeddance_reference_image_url(request_obj)
        if not reference_image_url:
            raise RuntimeError("seeddance-1.5-pro requires a reference image url")
        prompt = self._enforce_video_hard_requirements(shaped_prompt)
        if len(prompt) > spec.prompt_limit:
            prompt = prompt[: spec.prompt_limit].rstrip()
        backend_model_name = (spec.backend_model_name or spec.name).strip()
        prompt_with_flags = f"{prompt} --duration {int(normalized_duration)} --camerafixed false --watermark true"
        body: dict[str, Any] = {
            "model": backend_model_name,
            "content": [
                {
                    "type": "text",
                    "text": prompt_with_flags,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": reference_image_url,
                    },
                },
            ],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-Api-Key": api_key,
            },
        )
        self._trace_call(
            call_chain,
            stage="remote_request",
            event="sent",
            status="ok",
            message="seeddance video task submitted",
            details={
                "modelName": spec.name,
                "backendModelName": backend_model_name,
                "provider": self.infer_video_provider(spec.name),
                "size": normalized_size,
                "durationSeconds": int(normalized_duration),
                "minDurationSeconds": min_requested_duration,
                "maxDurationSeconds": max_requested_duration,
                "referenceImageUrl": reference_image_url,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            detail_text = truncate_text(detail.strip(), 320)
            if detail_text:
                raise RuntimeError(f"seeddance video task submit http error: {exc.code} {detail_text}") from exc
            raise RuntimeError(f"seeddance video task submit http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"seeddance video task submit network error: {exc}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"seeddance video task submit timeout: {exc}") from exc

        payload = self._parse_json_bytes(raw_response)
        task_id = self._extract_task_id(payload)
        if not task_id:
            raise RuntimeError("seeddance video task response missing task id")

        self._trace_call(
            call_chain,
            stage="task",
            event="created",
            status="ok",
            message="seeddance task created",
            details={"taskId": task_id},
        )
        task_marker = f"[seeddance_task_id={task_id}]"
        try:
            poll_result = self._poll_seeddance_video_task(
                task_id=task_id,
                task_endpoint=task_endpoint,
                api_key=api_key,
                call_chain=call_chain,
            )
        except Exception as exc:
            raise RuntimeError(
                truncate_text(f"{task_marker} seeddance task poll failed: {exc}", 700)
                or f"{task_marker} seeddance task poll failed"
            ) from exc
        video_url = self._extract_video_url(poll_result)
        if not video_url:
            output_block = poll_result.get("output") if isinstance(poll_result.get("output"), dict) else {}
            data_block = poll_result.get("data") if isinstance(poll_result.get("data"), dict) else {}
            raise RuntimeError(
                truncate_text(
                    (
                        f"{task_marker} seeddance task completed without video_url; "
                        f"payload_keys={list(poll_result.keys())[:10]}, "
                        f"output_keys={list(output_block.keys())[:10]}, "
                        f"data_keys={list(data_block.keys())[:10]}"
                    ),
                    500,
                )
                or f"{task_marker} seeddance task completed without video_url"
            )
        try:
            data, mime_type = self._download_binary(
                video_url,
                call_chain=call_chain,
                timeout_seconds=max(float(self.settings.model.timeout_seconds), 300.0),
            )
        except Exception as exc:
            raise RuntimeError(
                truncate_text(f"{task_marker} seeddance video download failed: {exc}", 700)
                or f"{task_marker} seeddance video download failed"
            ) from exc
        mime_type = mime_type or "video/mp4"
        output_path = self._prepare_output_path(generation_id, "video", self._extension_from_mime_or_url(mime_type, video_url, "video"))
        output_path.write_bytes(data)
        return {
            "path": output_path,
            "mimeType": mime_type,
            "metadata": {
                "remoteSourceUrl": video_url,
                "byteSize": output_path.stat().st_size,
                "aspectRatio": self._aspect_ratio_label(normalized_width, normalized_height),
                "resolution": f"{normalized_width}x{normalized_height}",
                "durationSeconds": int(normalized_duration),
                "requestedMinDurationSeconds": min_requested_duration,
                "requestedMaxDurationSeconds": max_requested_duration,
                "taskId": task_id,
                "providerModel": spec.name,
                "taskStatus": "SUCCEEDED",
                "actualPrompt": prompt_with_flags,
                "referenceImageUrl": reference_image_url,
                "modelInfo": {
                    "provider": self.infer_video_provider(spec.name),
                    "modelName": backend_model_name,
                    "providerModel": spec.name,
                    "endpointHost": urllib.parse.urlparse(endpoint).netloc or endpoint,
                    "taskEndpointHost": urllib.parse.urlparse(task_endpoint).netloc or task_endpoint,
                    "taskId": task_id,
                    "mediaKind": "video",
                },
            },
        }

    def _resolve_seeddance_reference_image_url(self, request_obj: GenerateTextMediaRequest) -> str:
        extras = getattr(request_obj, "extras", None)
        if not isinstance(extras, dict):
            return ""
        for key in ("imageUrl", "image_url", "referenceImageUrl", "reference_image_url", "sourceImageUrl"):
            value = extras.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _generate_dashscope_video(
        self,
        *,
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        endpoint = self._resolve_video_endpoint()
        task_endpoint = self._resolve_video_task_endpoint()
        if not endpoint:
            raise RuntimeError("video endpoint is empty")
        if not task_endpoint:
            raise RuntimeError("video task endpoint is empty")
        if not self.settings.model.api_key:
            raise RuntimeError("model api_key is empty")

        spec = self._resolve_video_model_spec(request_obj)
        backend_model_name = (spec.backend_model_name or spec.name).strip() or spec.name
        width, height = self._resolve_dimensions(request_obj)
        normalized_width, normalized_height, normalized_size = self._normalize_video_size(
            spec=spec,
            width=width,
            height=height,
        )
        requested_duration, min_requested_duration, max_requested_duration = self._resolve_requested_video_duration_bounds(request_obj)
        normalized_duration = self._normalize_video_duration(
            spec=spec,
            requested=requested_duration,
            min_requested=min_requested_duration,
            max_requested=max_requested_duration,
        )

        if normalized_width != width or normalized_height != height:
            self._trace_call(
                call_chain,
                stage="request",
                event="normalize_size",
                status="ok",
                message="video size adjusted to provider-supported resolution",
                details={
                    "requested": f"{width}x{height}",
                    "normalized": normalized_size.replace("*", "x"),
                    "modelName": spec.name,
                },
            )

        duration_adjusted = (
            (requested_duration is not None and abs(requested_duration - normalized_duration) > 0.01)
            or (min_requested_duration is not None and normalized_duration < min_requested_duration)
            or (max_requested_duration is not None and normalized_duration > max_requested_duration)
        )
        if duration_adjusted:
            self._trace_call(
                call_chain,
                stage="request",
                event="normalize_duration",
                status="ok",
                message="video duration adjusted to provider-supported range",
                details={
                    "requested": requested_duration,
                    "requestedMinDurationSeconds": min_requested_duration,
                    "requestedMaxDurationSeconds": max_requested_duration,
                    "normalized": normalized_duration,
                    "modelName": spec.name,
                },
            )

        prompt = self._enforce_video_hard_requirements(shaped_prompt)
        if len(prompt) > spec.prompt_limit:
            prompt = prompt[: spec.prompt_limit].rstrip()
            self._trace_call(
                call_chain,
                stage="prompt",
                event="truncate",
                status="ok",
                message="prompt truncated to provider limit",
                details={"promptLimit": spec.prompt_limit, "modelName": spec.name},
            )

        body: dict[str, Any] = {
            "model": backend_model_name,
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": normalized_size,
                "prompt_extend": bool(self.settings.model.video_prompt_extend),
            },
        }
        if not spec.is_fixed_duration:
            body["parameters"]["duration"] = int(normalized_duration)

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.model.api_key}",
                "X-DashScope-Async": "enable",
            },
        )
        self._trace_call(
            call_chain,
            stage="remote_request",
            event="sent",
            status="ok",
            message="dashscope video task submitted",
            details={
                "modelName": spec.name,
                "backendModelName": backend_model_name,
                "provider": self.infer_video_provider(spec.name),
                "size": normalized_size,
                "durationSeconds": int(normalized_duration),
                "minDurationSeconds": min_requested_duration,
                "maxDurationSeconds": max_requested_duration,
                "promptExtend": bool(self.settings.model.video_prompt_extend),
            },
        )

        request_started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw_response = response.read()
            elapsed_ms = int((time.perf_counter() - request_started) * 1000)
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="ok",
                message="dashscope task creation response received",
                details={"byteSize": len(raw_response), "elapsedMs": elapsed_ms},
            )
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"dashscope video task submit timeout: {exc}") from exc
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"dashscope video task submit http error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"dashscope video task submit network error: {exc}") from exc

        payload = self._parse_json_bytes(raw_response)
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        task_id = str(output.get("task_id") or output.get("taskId") or payload.get("task_id") or "").strip()
        if not task_id:
            raise RuntimeError("dashscope video task response missing task_id")

        request_id = str(payload.get("request_id") or payload.get("requestId") or "").strip() or None
        self._trace_call(
            call_chain,
            stage="task",
            event="created",
            status="ok",
            message="dashscope task created",
            details={"taskId": task_id, "requestId": request_id},
        )

        poll_result = self._poll_dashscope_video_task(
            task_id=task_id,
            task_endpoint=task_endpoint,
            call_chain=call_chain,
        )
        video_url = self._extract_video_url(poll_result)
        if not video_url:
            raise RuntimeError("dashscope task completed without video_url")

        data, mime_type = self._download_binary(
            video_url,
            call_chain=call_chain,
            timeout_seconds=max(float(self.settings.model.timeout_seconds), 300.0),
        )
        mime_type = mime_type or "video/mp4"
        output_path = self._prepare_output_path(generation_id, "video", self._extension_from_mime_or_url(mime_type, video_url, "video"))
        output_path.write_bytes(data)
        self._trace_call(
            call_chain,
            stage="output",
            event="saved",
            status="ok",
            message="generated video file saved",
            details={
                "filePath": output_path.as_posix(),
                "mimeType": mime_type,
                "byteSize": output_path.stat().st_size,
            },
        )

        output_block = poll_result.get("output") if isinstance(poll_result.get("output"), dict) else {}
        remote_prompt = str(output_block.get("orig_prompt") or output_block.get("actual_prompt") or "").strip() or None
        return {
            "path": output_path,
            "mimeType": mime_type,
            "metadata": {
                "remoteSourceUrl": video_url,
                "byteSize": output_path.stat().st_size,
                "aspectRatio": self._aspect_ratio_label(normalized_width, normalized_height),
                "resolution": f"{normalized_width}x{normalized_height}",
                "durationSeconds": int(normalized_duration),
                "requestedMinDurationSeconds": min_requested_duration,
                "requestedMaxDurationSeconds": max_requested_duration,
                "taskId": task_id,
                "requestId": request_id,
                "providerModel": spec.name,
                "backendModelName": backend_model_name,
                "taskStatus": str(output_block.get("task_status") or output_block.get("taskStatus") or "SUCCEEDED"),
                "submitTime": output_block.get("submit_time"),
                "scheduledTime": output_block.get("scheduled_time"),
                "endTime": output_block.get("end_time"),
                "stylePreset": getattr(request_obj, "stylePreset", None),
                "actualPrompt": remote_prompt,
                "modelInfo": {
                    "provider": self.infer_video_provider(spec.name),
                    "modelName": backend_model_name,
                    "providerModel": spec.name,
                    "endpointHost": urllib.parse.urlparse(endpoint).netloc or endpoint,
                    "taskEndpointHost": urllib.parse.urlparse(task_endpoint).netloc or task_endpoint,
                    "taskId": task_id,
                    "promptExtend": bool(self.settings.model.video_prompt_extend),
                    "mediaKind": "video",
                },
            },
        }

    def _poll_dashscope_video_task(
        self,
        *,
        task_id: str,
        task_endpoint: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(30.0, float(self.settings.model.video_poll_timeout_seconds))
        interval = max(1.0, float(self.settings.model.video_poll_interval_seconds))
        poll_url = f"{task_endpoint.rstrip('/')}/{urllib.parse.quote(task_id)}"
        attempt = 0
        last_payload: dict[str, Any] = {}

        while time.monotonic() < deadline:
            attempt += 1
            request = urllib.request.Request(
                poll_url,
                headers={
                    "Authorization": f"Bearer {self.settings.model.api_key}",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                    raw_response = response.read()
            except (TimeoutError, socket.timeout) as exc:
                self._trace_call(
                    call_chain,
                    stage="task_poll",
                    event="attempt",
                    status="retry",
                    message="dashscope task poll timeout, will retry",
                    details={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(interval)
                continue
            except urllib.error.HTTPError as exc:
                self._trace_call(
                    call_chain,
                    stage="task_poll",
                    event="attempt",
                    status="retry" if int(exc.code) >= 500 else "error",
                    message="dashscope task poll http error",
                    details={"attempt": attempt, "statusCode": int(exc.code)},
                )
                if int(exc.code) >= 500:
                    time.sleep(interval)
                    continue
                raise RuntimeError(f"dashscope task poll http error: {exc.code}") from exc
            except urllib.error.URLError as exc:
                self._trace_call(
                    call_chain,
                    stage="task_poll",
                    event="attempt",
                    status="retry",
                    message="dashscope task poll network error, will retry",
                    details={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(interval)
                continue

            payload = self._parse_json_bytes(raw_response)
            last_payload = payload
            output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
            task_status = str(output.get("task_status") or output.get("taskStatus") or "").upper()
            self._trace_call(
                call_chain,
                stage="task_poll",
                event="attempt",
                status="ok",
                message="dashscope task polled",
                details={"attempt": attempt, "taskStatus": task_status or "UNKNOWN"},
            )

            if task_status == "SUCCEEDED":
                return payload
            if task_status in {"FAILED", "CANCELED", "CANCELLED"}:
                message = str(output.get("message") or payload.get("message") or "dashscope task failed")
                raise RuntimeError(message)
            time.sleep(interval)

        raise RuntimeError(
            truncate_text(
                f"dashscope task poll timeout for task {task_id}; last payload keys={list(last_payload.keys())[:8]}",
                400,
            )
            or f"dashscope task poll timeout for task {task_id}"
        )

    def _poll_seeddance_video_task(
        self,
        *,
        task_id: str,
        task_endpoint: str,
        api_key: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(30.0, float(self.settings.model.seeddance_poll_timeout_seconds))
        interval = max(1.0, float(self.settings.model.seeddance_poll_interval_seconds))
        poll_url = f"{task_endpoint.rstrip('/')}/{urllib.parse.quote(task_id)}"
        attempt = 0
        last_payload: dict[str, Any] = {}

        while time.monotonic() < deadline:
            attempt += 1
            request = urllib.request.Request(
                poll_url,
                method="GET",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "X-Api-Key": api_key,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                    raw_response = response.read()
            except (TimeoutError, socket.timeout):
                time.sleep(interval)
                continue
            except urllib.error.HTTPError as exc:
                if int(exc.code) >= 500:
                    time.sleep(interval)
                    continue
                raise RuntimeError(f"seeddance task poll http error: {exc.code}") from exc
            except urllib.error.URLError as exc:
                time.sleep(interval)
                if attempt < 3:
                    continue
                raise RuntimeError(f"seeddance task poll network error: {exc}") from exc

            payload = self._parse_json_bytes(raw_response)
            last_payload = payload
            task_status = str(
                self._first_str(
                    payload,
                    ("task_status", "taskStatus", "status", "state"),
                )
                or self._first_str(payload.get("output") if isinstance(payload.get("output"), dict) else {}, ("task_status", "taskStatus", "status", "state"))
                or self._first_str(payload.get("data") if isinstance(payload.get("data"), dict) else {}, ("task_status", "taskStatus", "status", "state"))
            ).upper()
            if task_status in {"SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED"}:
                return payload
            if task_status in {"FAILED", "FAIL", "CANCELED", "CANCELLED"}:
                message = self._first_str(payload, ("message", "error")) or "seeddance task failed"
                raise RuntimeError(message)
            self._trace_call(
                call_chain,
                stage="task_poll",
                event="attempt",
                status="ok",
                message="seeddance task polled",
                details={"attempt": attempt, "taskStatus": task_status or "UNKNOWN"},
            )
            time.sleep(interval)
        raise RuntimeError(
            truncate_text(
                f"seeddance task poll timeout for task {task_id}; last payload keys={list(last_payload.keys())[:8]}",
                400,
            )
            or f"seeddance task poll timeout for task {task_id}"
        )

    def _parse_json_bytes(self, raw: bytes) -> dict[str, Any]:
        return parse_json_bytes(raw)

    def _extract_media_blob(
        self,
        *,
        media_type: Literal["image", "video"],
        payload: dict[str, Any],
        raw_text: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        download_errors: list[str] = []
        url_keys = (
            "url",
            "file_url",
            "fileUrl",
            "media_url",
            "mediaUrl",
            "download_url",
            "downloadUrl",
            "image_url",
            "imageUrl",
            "video_url",
            "videoUrl",
            "output_url",
            "outputUrl",
            "result_url",
            "resultUrl",
        )
        base64_keys = (
            "b64_json",
            "base64",
            "base64_data",
            "base64Data",
            "image_base64",
            "imageBase64",
            "data",
        )
        mime_keys = ("mime_type", "mimeType", "content_type", "contentType")

        def _decode_data_url(value: str) -> dict[str, Any] | None:
            normalized = value.strip()
            if not normalized.lower().startswith("data:"):
                return None
            header, sep, encoded = normalized.partition(",")
            if not sep:
                return None
            mime_section = header[5:]
            mime_type = mime_section.split(";", 1)[0].strip()
            if ";base64" in header.lower():
                data = self._decode_base64_blob(encoded)
            else:
                data = urllib.parse.unquote_to_bytes(encoded)
            return {"data": data, "mimeType": mime_type, "sourceUrl": ""}

        def _extract_candidate_url(candidate: dict[str, Any]) -> str:
            direct = self._first_str(candidate, url_keys)
            if direct:
                return direct
            for key in url_keys:
                value = candidate.get(key)
                if isinstance(value, dict):
                    nested = self._first_str(value, ("url", "href", "uri"))
                    if nested:
                        return nested
            return ""

        def _extract_candidate_base64(candidate: dict[str, Any]) -> str:
            direct = self._first_str(candidate, base64_keys)
            if direct:
                return direct
            for key in base64_keys:
                value = candidate.get(key)
                if isinstance(value, dict):
                    nested = self._first_str(value, base64_keys)
                    if nested:
                        return nested
            return ""

        def _try_download(url: str) -> dict[str, Any] | None:
            data_url_blob = _decode_data_url(url)
            if data_url_blob is not None:
                return data_url_blob
            try:
                data, mime_type = self._download_binary(url, call_chain=call_chain)
                return {"data": data, "mimeType": mime_type, "sourceUrl": url}
            except Exception as exc:
                download_errors.append(str(exc))
                return None

        def _try_mapping(candidate: dict[str, Any], source: str) -> dict[str, Any] | None:
            url = _extract_candidate_url(candidate)
            if url:
                self._trace_call(
                    call_chain,
                    stage="media_extract",
                    event="candidate_url",
                    status="ok",
                    message=f"found media url in {source}",
                    details={"url": url[:240]},
                )
                downloaded = _try_download(url)
                if downloaded is not None:
                    return downloaded
            b64 = _extract_candidate_base64(candidate)
            if b64:
                self._trace_call(
                    call_chain,
                    stage="media_extract",
                    event="base64",
                    status="ok",
                    message=f"using base64 payload from {source}",
                )
                mime_type = self._first_str(candidate, mime_keys) or ""
                data = self._decode_base64_blob(b64)
                return {"data": data, "mimeType": mime_type, "sourceUrl": ""}
            return None

        top_output = payload.get("output") if isinstance(payload.get("output"), dict) else None
        top_data = payload.get("data") if isinstance(payload.get("data"), dict) else None

        for source, candidate in (
            ("payload", payload),
            ("payload.output", top_output),
            ("payload.data", top_data),
        ):
            if isinstance(candidate, dict):
                resolved = _try_mapping(candidate, source)
                if resolved is not None:
                    return resolved

        if isinstance(payload.get("data"), list):
            for index, item in enumerate(payload["data"]):
                if not isinstance(item, dict):
                    continue
                resolved = _try_mapping(item, f"payload.data[{index}]")
                if resolved is not None:
                    return resolved

        for container, source_prefix in ((top_output, "payload.output"), (top_data, "payload.data"), (payload, "payload")):
            if not isinstance(container, dict):
                continue
            for list_key in ("results", "images", "outputs", "items"):
                values = container.get(list_key)
                if not isinstance(values, list):
                    continue
                for index, item in enumerate(values):
                    if not isinstance(item, dict):
                        continue
                    resolved = _try_mapping(item, f"{source_prefix}.{list_key}[{index}]")
                    if resolved is not None:
                        return resolved

        model_json = self._extract_json_from_model_payload(payload, raw_text)
        resolved_model_json = _try_mapping(model_json, "model_json")
        if resolved_model_json is not None:
            return resolved_model_json

        if download_errors:
            joined = " | ".join(download_errors)
            self._trace_call(
                call_chain,
                stage="media_extract",
                event="download",
                status="error",
                message="all media download attempts failed",
                details={"error": truncate_text(joined, 500) or joined},
            )
            raise RuntimeError(truncate_text(f"remote media download failed: {joined}", 600) or joined)
        return None

    def _extract_json_from_model_payload(self, payload: dict[str, Any], raw_text: str) -> dict[str, Any]:
        if isinstance(payload.get("choices"), list) and payload["choices"]:
            first_choice = payload["choices"][0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message") or {}
                content = message.get("content")
                if isinstance(content, str):
                    parsed, _ = parse_json_object(content)
                    if parsed:
                        return parsed
                if isinstance(content, list):
                    chunks: list[str] = []
                    for item in content:
                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                            chunks.append(item["text"])
                    if chunks:
                        parsed, _ = parse_json_object("\n".join(chunks))
                        if parsed:
                            return parsed

        if isinstance(payload.get("output"), dict):
            output = payload["output"]
            for key in ("text", "content"):
                content = output.get(key)
                if isinstance(content, str):
                    parsed, _ = parse_json_object(content)
                    if parsed:
                        return parsed

        parsed_raw, _ = parse_json_object(raw_text)
        return parsed_raw

    def _extract_text_response(self, payload: dict[str, Any], raw_text: str) -> str:
        primary = extract_llm_text_response(payload, raw_text).strip()
        chunks: list[str] = []
        if isinstance(payload.get("choices"), list):
            for choice in payload["choices"]:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message")
                if isinstance(message, dict):
                    chunks.extend(self._collect_text_chunks(message.get("content")))
                chunks.extend(self._collect_text_chunks(choice.get("text")))
        chunks.extend(self._collect_text_chunks(payload.get("output_text")))
        chunks.extend(self._collect_text_chunks(payload.get("output")))
        if isinstance(payload.get("message"), dict):
            chunks.extend(self._collect_text_chunks(payload["message"].get("content")))
        merged = self._merge_text_chunks(chunks)
        if merged:
            return merged
        failure_message = self._extract_response_failure_message(payload)
        if failure_message:
            raise RuntimeError(f"remote text response failed: {failure_message}")
        return primary

    def _extract_response_failure_message(self, payload: dict[str, Any]) -> str | None:
        status = str(payload.get("status") or "").strip().lower()
        failed_status = status in {"failed", "error", "cancelled", "canceled"}
        error_value = payload.get("error")
        if isinstance(error_value, dict):
            code = str(error_value.get("code") or "").strip()
            message = str(error_value.get("message") or error_value.get("msg") or "").strip()
            if code and message:
                return f"{code}: {message}"
            if message:
                return message
            if code:
                return code
        elif isinstance(error_value, str) and error_value.strip():
            return error_value.strip()
        if failed_status:
            return f"status={status}"
        return None

    def _collect_text_chunks(self, value: Any) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, list):
            chunks: list[str] = []
            for item in value:
                chunks.extend(self._collect_text_chunks(item))
            return chunks
        if isinstance(value, dict):
            chunks: list[str] = []
            for key in ("text", "output_text"):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    chunks.append(item.strip())
            for key in ("content", "parts"):
                item = value.get(key)
                if isinstance(item, (str, list, dict)):
                    chunks.extend(self._collect_text_chunks(item))
            return chunks
        return []

    def _merge_text_chunks(self, chunks: list[str]) -> str:
        merged = ""
        for chunk in chunks:
            piece = str(chunk or "").strip()
            if not piece:
                continue
            if not merged:
                merged = piece
                continue
            if len(piece) > 80 and piece in merged:
                continue
            max_overlap = min(len(merged), len(piece), 260)
            overlap = 0
            for size in range(max_overlap, 16, -1):
                if merged.endswith(piece[:size]):
                    overlap = size
                    break
            if overlap > 0:
                merged += piece[overlap:]
                continue
            joiner = "" if merged.endswith(("\n", "\r", " ")) else "\n"
            merged += f"{joiner}{piece}"
        return merged.strip()

    def _decode_base64_blob(self, value: str) -> bytes:
        normalized = value.strip()
        if "base64," in normalized:
            normalized = normalized.split("base64,", 1)[1]
        remainder = len(normalized) % 4
        if remainder:
            normalized += "=" * (4 - remainder)
        try:
            return base64.b64decode(normalized, validate=False)
        except Exception as exc:
            raise RuntimeError("invalid base64 payload from remote provider") from exc

    def _download_binary(
        self,
        url: str,
        *,
        call_chain: list[dict[str, Any]] | None = None,
        timeout_seconds: float | None = None,
    ) -> tuple[bytes, str]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ai-cut/0.1",
                "Accept": "*/*",
            },
        )
        last_exc: Exception | None = None
        for attempt in range(3):
            if call_chain is not None:
                self._trace_call(
                    call_chain,
                    stage="remote_download",
                    event="attempt",
                    status="ok",
                    message="downloading remote media url",
                    details={"attempt": attempt + 1, "url": url[:240]},
                )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=timeout_seconds if timeout_seconds is not None else self.settings.model.timeout_seconds,
                ) as response:
                    data = response.read()
                    mime_type = response.headers.get_content_type() or ""
                    if call_chain is not None:
                        self._trace_call(
                            call_chain,
                            stage="remote_download",
                            event="attempt",
                            status="ok",
                            message="remote media download succeeded",
                            details={
                                "attempt": attempt + 1,
                                "byteSize": len(data),
                                "mimeType": mime_type,
                            },
                        )
                    return data, mime_type
            except (TimeoutError, socket.timeout) as exc:
                last_exc = exc
                if attempt < 2:
                    if call_chain is not None:
                        self._trace_call(
                            call_chain,
                            stage="remote_download",
                            event="attempt",
                            status="retry",
                            message="remote media download timeout, will retry",
                            details={"attempt": attempt + 1, "error": str(exc)},
                        )
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise RuntimeError(f"remote media download timeout: {exc}") from exc
            except urllib.error.HTTPError as exc:
                last_exc = exc
                status_code = int(exc.code)
                should_retry = status_code >= 500 or status_code == 429
                if should_retry and attempt < 2:
                    if call_chain is not None:
                        self._trace_call(
                            call_chain,
                            stage="remote_download",
                            event="attempt",
                            status="retry",
                            message="remote media download http error, will retry",
                            details={"attempt": attempt + 1, "statusCode": status_code},
                        )
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise RuntimeError(f"remote media download http error: {exc.code}") from exc
            except urllib.error.URLError as exc:
                last_exc = exc
                if attempt < 2:
                    if call_chain is not None:
                        self._trace_call(
                            call_chain,
                            stage="remote_download",
                            event="attempt",
                            status="retry",
                            message="remote media download network error, will retry",
                            details={"attempt": attempt + 1, "error": str(exc)},
                        )
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise RuntimeError(f"remote media download network error: {exc}") from exc
        raise RuntimeError(f"remote media download failed: {last_exc}")

    def _generate_local_media(
        self,
        *,
        media_type: Literal["image", "video"],
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
    ) -> dict[str, Any]:
        if media_type == "image":
            path = self._generate_local_svg(request_obj, profile, shaped_prompt, generation_id)
            return {
                "path": path,
                "mimeType": "image/svg+xml",
                "metadata": {"byteSize": path.stat().st_size, "engine": "local-svg"},
            }
        path, drawtext_applied, duration_seconds = self._generate_local_video(request_obj, profile, shaped_prompt, generation_id)
        return {
            "path": path,
            "mimeType": "video/mp4",
            "metadata": {
                "byteSize": path.stat().st_size,
                "engine": "local-ffmpeg",
                "drawtextApplied": drawtext_applied,
                "durationSeconds": duration_seconds,
            },
        }

    def _generate_local_svg(
        self,
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
    ) -> Path:
        width, height = self._resolve_dimensions(request_obj)
        output_path = self._prepare_output_path(generation_id, "image", "svg")

        prompt = str(getattr(request_obj, "prompt", "")).strip()
        title_text = truncate_text(prompt, 120) or "text-to-image"
        subtitle_text = truncate_text(shaped_prompt, 240) or profile.image_prompt_style
        title_lines = self._split_text_lines(title_text, line_length=20, limit=3)
        subtitle_lines = self._split_text_lines(subtitle_text, line_length=34, limit=5)

        title_y = int(height * 0.34)
        subtitle_y = int(height * 0.52)
        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            '  <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
            f'    <stop offset="0%" stop-color="{profile.image_gradient_start}"/>',
            f'    <stop offset="100%" stop-color="{profile.image_gradient_end}"/>',
            "  </linearGradient>",
            "</defs>",
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg)"/>',
            f'<circle cx="{int(width * 0.82)}" cy="{int(height * 0.17)}" r="{int(min(width, height) * 0.11)}" fill="white" fill-opacity="0.08"/>',
            f'<rect x="{int(width * 0.08)}" y="{int(height * 0.16)}" width="{int(width * 0.84)}" height="{int(height * 0.68)}" rx="28" fill="black" fill-opacity="0.22"/>',
        ]

        title_line_step = int(height * 0.056)
        subtitle_line_step = int(height * 0.033)
        for index, line in enumerate(title_lines):
            svg_parts.append(
                f'<text x="{int(width * 0.1)}" y="{title_y + (index * title_line_step)}" '
                f'font-family="Arial, sans-serif" font-size="{int(height * 0.05)}" '
                f'font-weight="700" fill="white">{html_escape(line)}</text>'
            )
        for index, line in enumerate(subtitle_lines):
            svg_parts.append(
                f'<text x="{int(width * 0.1)}" y="{subtitle_y + (index * subtitle_line_step)}" '
                f'font-family="Arial, sans-serif" font-size="{int(height * 0.026)}" '
                f'fill="white" fill-opacity="0.92">{html_escape(line)}</text>'
            )
        svg_parts.append("</svg>")
        output_path.write_text("\n".join(svg_parts), encoding="utf-8")
        return output_path

    def _generate_local_video(
        self,
        request_obj: GenerateTextMediaRequest,
        profile: _VersionProfile,
        shaped_prompt: str,
        generation_id: str,
    ) -> tuple[Path, bool, int]:
        width, height = self._resolve_dimensions(request_obj)
        spec = self._resolve_video_model_spec(request_obj)
        requested_duration, min_duration, max_duration = self._resolve_requested_video_duration_bounds(request_obj)
        normalized_duration = self._normalize_video_duration(
            spec=spec,
            requested=requested_duration,
            min_requested=min_duration,
            max_requested=max_duration,
        )
        safe_duration = max(1.0, min(30.0, float(normalized_duration)))
        output_path = self._prepare_output_path(generation_id, "video", "mp4")

        overlay_text = truncate_text(shaped_prompt, 110) or profile.video_prompt_style
        escaped_text = self._escape_ffmpeg_text(overlay_text)
        font_size = max(28, int(min(width, height) * 0.04))
        drawtext_filter = (
            f"drawtext=text='{escaped_text}':fontcolor=white:fontsize={font_size}:"
            "x=(w-text_w)/2:y=h*0.78:line_spacing=8:box=1:boxcolor=black@0.40:boxborderw=18"
        )

        drawtext_command = [
            self.ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={profile.video_color}:s={width}x{height}:r=30:d={safe_duration:.3f}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-vf",
            drawtext_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        try:
            self._run_command(drawtext_command)
            return output_path, True, int(normalized_duration)
        except Exception:
            color_only_command = [
                self.ffmpeg_bin,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={profile.video_color}:s={width}x{height}:r=30:d={safe_duration:.3f}",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            self._run_command(color_only_command)
            return output_path, False, int(normalized_duration)

    def _run_command(self, command: list[str]) -> None:
        try:
            completed = subprocess.run(command, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"{command[0]} is not installed or not available in PATH") from exc
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "command failed"
            raise RuntimeError(stderr)

    def _enforce_video_hard_requirements(self, prompt: str) -> str:
        base_prompt = prompt.strip()
        hard_requirement = (
            "硬性要求（必须满足）：镜头转换连贯衔接，不打断对白，不在一句对白中途切断；"
            "前后片段声音必须自然过渡，禁止上一段声音戛然而止后下一段声音立即硬切。"
        )
        if hard_requirement in base_prompt:
            return base_prompt
        if not base_prompt:
            return hard_requirement
        return f"{hard_requirement} {base_prompt}"

    def _shape_prompt(
        self,
        media_type: Literal["image", "video"],
        prompt: str,
        profile: _VersionProfile,
        extras: dict[str, Any],
    ) -> str:
        style_hint = str(extras.get("styleHint", "")).strip()
        camera_hint = str(extras.get("cameraHint", "")).strip()
        lighting_hint = str(extras.get("lightingHint", "")).strip()
        subject = prompt.strip() or "untitled concept"
        if media_type == "image":
            parts = [
                profile.image_prompt_style,
                f"Subject: {subject}.",
            ]
            if style_hint:
                parts.append(f"Additional style: {style_hint}.")
            if lighting_hint:
                parts.append(f"Lighting: {lighting_hint}.")
            parts.append("Deliver a single coherent frame with clear focal hierarchy.")
            return " ".join(parts)

        parts = [
            profile.video_prompt_style,
            f"Core concept: {subject}.",
        ]
        if style_hint:
            parts.append(f"Visual style: {style_hint}.")
        if camera_hint:
            parts.append(f"Camera direction: {camera_hint}.")
        if lighting_hint:
            parts.append(f"Lighting direction: {lighting_hint}.")
        parts.append("Deliver one short shot concept with beginning, motion beat, and end beat.")
        return self._enforce_video_hard_requirements(" ".join(parts))

    def _build_response(
        self,
        *,
        media_type: Literal["image", "video"],
        generation_id: str,
        version: str,
        prompt: str,
        shaped_prompt: str,
        source: str,
        request_obj: GenerateTextMediaRequest,
        output_path: Path,
        mime_type: str,
        metadata: dict[str, Any],
    ) -> GenerateTextMediaResponse:
        relative = output_path.resolve().relative_to(self.storage.root.resolve()).as_posix()
        width, height = self._resolve_dimensions(request_obj)
        duration_seconds = None
        if media_type == "video":
            metadata_duration = metadata.get("durationSeconds")
            if isinstance(metadata_duration, (int, float)):
                duration_seconds = float(metadata_duration)
            else:
                requested_duration = getattr(request_obj, "durationSeconds", None)
                duration_seconds = float(requested_duration) if requested_duration not in {None, ""} else None
        version_int = int(version.lstrip("v") or "1")
        enriched_metadata = dict(metadata)
        enriched_metadata.setdefault("version", version_int)
        enriched_metadata.setdefault("shapedPrompt", shaped_prompt)
        enriched_metadata.setdefault("filePath", relative)
        enriched_metadata.setdefault("mimeType", mime_type)
        enriched_metadata.setdefault("source", source)
        created_at = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        payload = {
            "id": generation_id,
            "kind": media_type,
            "version": version_int,
            "prompt": prompt,
            "outputUrl": self.storage.build_public_url(relative),
            "durationSeconds": duration_seconds,
            "width": width,
            "height": height,
            "status": "completed",
            "createdAt": created_at,
            "metadata": enriched_metadata,
            "generationId": generation_id,
            "mediaType": media_type,
            "shapedPrompt": shaped_prompt,
            "source": source,
            "filePath": relative,
            "fileUrl": self.storage.build_public_url(relative),
            "mimeType": mime_type,
            "stylePreset": enriched_metadata.get("stylePreset"),
            "thumbnailUrl": enriched_metadata.get("thumbnailUrl"),
            "modelInfo": enriched_metadata.get("modelInfo"),
            "callChain": enriched_metadata.get("callChain"),
        }
        return self._build_model(GenerateTextMediaResponse, payload)

    def _build_model(self, model_class: Any, payload: dict[str, Any]) -> Any:
        if hasattr(model_class, "model_validate"):
            return model_class.model_validate(payload)
        return model_class(**payload)

    def _resolve_video_model_spec(self, request_obj: GenerateTextMediaRequest | None = None) -> _VideoModelSpec:
        raw_name = ""
        if request_obj is not None:
            raw_name = str(
                getattr(request_obj, "videoModel", None)
                or getattr(request_obj, "providerModel", None)
                or ""
            ).strip().lower()
        if not raw_name:
            raw_name = str(self.settings.model.video_model_name or "").strip().lower()
        if not raw_name:
            raw_name = "wan2.6-i2v"
        normalized_name = _normalize_video_model_name(raw_name)
        if not normalized_name:
            normalized_name = "wan2.6-i2v"
        spec = _VIDEO_MODELS.get(normalized_name)
        if spec is None:
            supported = ", ".join(sorted(_VIDEO_MODELS))
            raise RuntimeError(f"unsupported video model '{raw_name}', supported models: {supported}")
        return spec

    def _resolve_video_endpoint(self) -> str:
        endpoint = str(self.settings.model.video_endpoint or "").strip()
        if endpoint:
            return endpoint
        base = str(self.settings.model.endpoint or "").strip()
        if not base:
            return ""
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/api/v1/services/aigc/video-generation/video-synthesis"
        return base.rstrip("/") + "/api/v1/services/aigc/video-generation/video-synthesis"

    def _resolve_video_task_endpoint(self) -> str:
        endpoint = str(self.settings.model.video_task_endpoint or "").strip()
        if endpoint:
            return endpoint
        base = self._resolve_video_endpoint()
        if not base:
            return ""
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/api/v1/tasks"
        return base.rstrip("/") + "/api/v1/tasks"

    def _resolve_seeddance_endpoint(self) -> str:
        endpoint = str(self.settings.model.seeddance_video_endpoint or "").strip()
        if endpoint:
            return endpoint
        return ""

    def _resolve_seedream_image_endpoint(self) -> str:
        candidates = (
            str(self.settings.model.seeddance_video_endpoint or "").strip(),
            str(self.settings.model.seeddance_video_task_endpoint or "").strip(),
            str(self.settings.model.endpoint or "").strip(),
        )
        for candidate in candidates:
            if not candidate:
                continue
            parsed = urllib.parse.urlparse(candidate)
            if parsed.scheme and parsed.netloc and "volces.com" in parsed.netloc.lower():
                return f"{parsed.scheme}://{parsed.netloc}/api/v3/images/generations"
        return "https://ark.cn-beijing.volces.com/api/v3/images/generations"

    def _resolve_seeddance_task_endpoint(self) -> str:
        endpoint = str(self.settings.model.seeddance_video_task_endpoint or "").strip()
        if endpoint:
            return endpoint
        return self._resolve_seeddance_endpoint()

    def _resolve_seeddance_api_key(self) -> str:
        explicit = str(self.settings.model.seeddance_api_key or "").strip()
        if explicit:
            return explicit
        return str(self.settings.model.api_key or "").strip()

    def _resolve_seedream_api_key(self) -> str:
        return self._resolve_seeddance_api_key()

    def _extract_task_id(self, payload: dict[str, Any]) -> str:
        candidates: list[Any] = [
            payload.get("task_id"),
            payload.get("taskId"),
            payload.get("id"),
        ]
        output = payload.get("output")
        if isinstance(output, dict):
            candidates.extend([output.get("task_id"), output.get("taskId"), output.get("id")])
        data = payload.get("data")
        if isinstance(data, dict):
            candidates.extend([data.get("task_id"), data.get("taskId"), data.get("id")])
        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""

    def extract_task_id(self, payload: dict[str, Any]) -> str:
        return self._extract_task_id(payload)

    def _normalize_video_size(self, *, spec: _VideoModelSpec, width: int, height: int) -> tuple[int, int, str]:
        requested = f"{width}*{height}"
        if requested in spec.supported_sizes:
            return width, height, requested

        requested_ratio = self._aspect_ratio_label(width, height)
        candidates: list[tuple[int, int]] = []
        for value in spec.supported_sizes:
            size_width, size_height = self._parse_video_size(value)
            if self._aspect_ratio_label(size_width, size_height) == requested_ratio:
                candidates.append((size_width, size_height))
        if not candidates:
            candidates = [self._parse_video_size(value) for value in spec.supported_sizes]

        selected_width, selected_height = max(candidates, key=lambda item: item[0] * item[1])
        return selected_width, selected_height, f"{selected_width}*{selected_height}"

    def _resolve_requested_video_duration_bounds(
        self,
        request_obj: GenerateTextMediaRequest,
    ) -> tuple[float | None, float | None, float | None]:
        requested_raw = getattr(request_obj, "durationSeconds", None)
        min_raw = getattr(request_obj, "minDurationSeconds", None)
        max_raw = getattr(request_obj, "maxDurationSeconds", None)
        requested = float(requested_raw) if requested_raw not in {None, ""} else None
        min_requested = float(min_raw) if min_raw not in {None, ""} else None
        max_requested = float(max_raw) if max_raw not in {None, ""} else None
        if requested is not None:
            if min_requested is None:
                min_requested = requested
            if max_requested is None:
                max_requested = requested
        return requested, min_requested, max_requested

    def _normalize_video_duration(
        self,
        *,
        spec: _VideoModelSpec,
        requested: float | None,
        min_requested: float | None,
        max_requested: float | None,
    ) -> int:
        if spec.is_fixed_duration:
            return spec.default_duration_seconds
        candidates = (
            list(spec.allowed_durations)
            if spec.allowed_durations
            else list(range(spec.min_duration_seconds, spec.max_duration_seconds + 1))
        )
        preferred = requested if requested is not None else float(spec.default_duration_seconds)
        in_range = [
            value for value in candidates
            if (min_requested is None or value >= min_requested)
            and (max_requested is None or value <= max_requested)
        ]
        pool = in_range or candidates
        if in_range:
            target = preferred
        elif min_requested is not None and max_requested is not None:
            target = (min_requested + max_requested) / 2
        elif min_requested is not None:
            target = min_requested
        elif max_requested is not None:
            target = max_requested
        else:
            target = preferred
        return min(pool, key=lambda value: (abs(value - target), abs(value - spec.default_duration_seconds), value))

    def _parse_video_size(self, value: str) -> tuple[int, int]:
        normalized = value.replace("x", "*").replace("X", "*")
        width_raw, _, height_raw = normalized.partition("*")
        return max(1, int(width_raw)), max(1, int(height_raw))

    def _extract_video_url(self, payload: dict[str, Any]) -> str:
        def _extract_from_mapping(mapping: dict[str, Any]) -> str:
            direct = self._first_str(
                mapping,
                ("video_url", "videoUrl", "url", "file_url", "fileUrl", "media_url", "mediaUrl"),
            )
            if direct:
                return direct
            for key in ("video_url", "videoUrl", "file_url", "fileUrl", "media_url", "mediaUrl", "url"):
                nested = mapping.get(key)
                if isinstance(nested, dict):
                    resolved = self._first_str(nested, ("url", "href", "uri"))
                    if resolved:
                        return resolved
            for nested_key in ("content", "result", "output", "data", "video", "media", "asset", "response"):
                nested_value = mapping.get(nested_key)
                if isinstance(nested_value, dict):
                    resolved = _extract_from_mapping(nested_value)
                    if resolved:
                        return resolved
                if isinstance(nested_value, list):
                    resolved = _extract_from_list(nested_value)
                    if resolved:
                        return resolved
            return ""

        def _extract_from_list(values: list[Any]) -> str:
            for item in values:
                if not isinstance(item, dict):
                    continue
                resolved = _extract_from_mapping(item)
                if resolved:
                    return resolved
                # 火山 contents/generations 常见格式：{"type":"video_url","video_url":{"url":"https://..."}}
                item_type = str(item.get("type") or "").strip().lower()
                if item_type in {"video_url", "video", "output_video"}:
                    nested = item.get("video_url") or item.get("videoUrl") or item.get("url")
                    if isinstance(nested, dict):
                        nested_url = self._first_str(nested, ("url", "href", "uri"))
                        if nested_url:
                            return nested_url
                for key in ("results", "videos", "items", "outputs", "content", "data", "choices"):
                    nested_values = item.get(key)
                    if isinstance(nested_values, list):
                        nested_url = _extract_from_list(nested_values)
                        if nested_url:
                            return nested_url
                    if isinstance(nested_values, dict):
                        nested_url = _extract_from_mapping(nested_values)
                        if nested_url:
                            return nested_url
            return ""

        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        data_block = payload.get("data") if isinstance(payload.get("data"), dict) else {}

        for mapping in (output, payload, data_block):
            if not isinstance(mapping, dict):
                continue
            resolved = _extract_from_mapping(mapping)
            if resolved:
                return resolved

        for container in (payload, output, data_block):
            if not isinstance(container, dict):
                continue
            for list_key in ("results", "videos", "items", "outputs", "content", "data", "choices"):
                values = container.get(list_key)
                if isinstance(values, list):
                    resolved = _extract_from_list(values)
                    if resolved:
                        return resolved
        return ""

    def extract_video_url(self, payload: dict[str, Any]) -> str:
        return self._extract_video_url(payload)

    def extract_task_status(self, payload: dict[str, Any]) -> str:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        status = (
            self._first_str(payload, ("task_status", "taskStatus", "status", "state"))
            or self._first_str(output, ("task_status", "taskStatus", "status", "state"))
            or self._first_str(data, ("task_status", "taskStatus", "status", "state"))
            or "UNKNOWN"
        )
        return status.upper()

    def extract_task_message(self, payload: dict[str, Any]) -> str | None:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        message = (
            self._first_str(payload, ("message", "error"))
            or self._first_str(output, ("message", "error"))
            or self._first_str(data, ("message", "error"))
        )
        return message or None

    def invoke_vision_model(self, *, model_name: str, body: dict[str, Any]) -> dict[str, Any]:
        endpoint = str(self.settings.model.endpoint or "").strip()
        api_key = str(self.settings.model.api_key or "").strip()
        if not endpoint:
            raise RuntimeError("vision model endpoint is empty")
        if not api_key:
            raise RuntimeError("vision model api key is empty")
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.model.timeout_seconds) as response:
                raw = response.read()
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"Vision request timed out ({model_name}): {exc}") from exc
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                body_text = ""
            raise RuntimeError(f"Vision request failed ({model_name}): {exc.code} {body_text[:400]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Vision request failed ({model_name}): {exc}") from exc
        return self._parse_json_bytes(raw)

    def _resolve_profile(self, version: int | str | None) -> _VersionProfile:
        if isinstance(version, int):
            normalized = f"v{version}"
        else:
            normalized = (version or "v1").strip().lower()
        if not normalized.startswith("v"):
            normalized = f"v{normalized}"
        return self._profiles.get(normalized, self._profiles["v1"])

    def _prepare_output_path(
        self,
        generation_id: str,
        media_type: Literal["image", "video"],
        extension: str,
    ) -> Path:
        date_label = datetime.utcnow().strftime("%Y%m%d")
        output_dir = self.storage.outputs_root / "text_generation" / date_label
        output_dir.mkdir(parents=True, exist_ok=True)
        normalized_ext = extension.strip(".").lower() or ("svg" if media_type == "image" else "mp4")
        return output_dir / f"{generation_id}_{media_type}.{normalized_ext}"

    def _resolution_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        if aspect_ratio == "16:9":
            return 1920, 1080
        return 1080, 1920

    def _resolve_dimensions(self, request_obj: GenerateTextMediaRequest) -> tuple[int, int]:
        width = int(getattr(request_obj, "width", 0) or 0)
        height = int(getattr(request_obj, "height", 0) or 0)
        if width > 0 and height > 0:
            return width, height
        ratio = str(getattr(request_obj, "aspectRatio", "9:16")).strip()
        return self._resolution_for_aspect_ratio(ratio)

    def _aspect_ratio_label(self, width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            return "9:16"
        divisor = gcd(width, height)
        if divisor <= 0:
            return f"{width}:{height}"
        simplified_width = width // divisor
        simplified_height = height // divisor
        return f"{simplified_width}:{simplified_height}"

    def _split_text_lines(self, text: str, line_length: int, limit: int) -> list[str]:
        cleaned = " ".join(text.replace("\n", " ").split())
        if not cleaned:
            return []
        lines: list[str] = []
        current = ""
        for token in cleaned.split(" "):
            if not token:
                continue
            candidate = f"{current} {token}".strip()
            if len(candidate) <= line_length:
                current = candidate
                continue
            if current:
                lines.append(current)
            if len(lines) >= limit:
                return lines[:limit]
            if len(token) > line_length:
                chunk = token[:line_length]
                lines.append(chunk)
                current = token[line_length:]
            else:
                current = token
            if len(lines) >= limit:
                return lines[:limit]
        if current and len(lines) < limit:
            lines.append(current)
        return lines[:limit]

    def _escape_ffmpeg_text(self, text: str) -> str:
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace(":", "\\:")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace("%", "\\%")
        escaped = escaped.replace("\n", "\\n")
        return escaped

    def _first_str(self, payload: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _coerce_extra_bool(self, value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _extension_from_mime_or_url(
        self,
        mime_type: str,
        source_url: str | None,
        media_type: Literal["image", "video"],
    ) -> str:
        mime = (mime_type or "").lower()
        if mime == "image/svg+xml":
            return "svg"
        if mime in {"image/png", "image/apng"}:
            return "png"
        if mime in {"image/jpeg", "image/jpg"}:
            return "jpg"
        if mime == "image/webp":
            return "webp"
        if mime == "video/mp4":
            return "mp4"
        if mime == "video/webm":
            return "webm"
        if source_url:
            path = urllib.parse.urlparse(source_url).path
            suffix = Path(path).suffix.strip(".").lower()
            if suffix:
                return suffix
        return "png" if media_type == "image" else "mp4"
