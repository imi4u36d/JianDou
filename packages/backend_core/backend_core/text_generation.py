from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape as html_escape
from math import gcd
from pathlib import Path
from typing import Any, Literal
import base64
import json
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel, Field, model_validator

from .config import Settings
from .storage import MediaStorage
from .utils import new_id, parse_json_object, truncate_text

_SchemaGenerationVersionInfo = None
_SchemaGenerationOptionsResponse = None
_SchemaGenerationVideoModelOption = None
_SchemaGenerationVideoSizeOption = None
_SchemaGenerateTextMediaRequest = None
_SchemaGenerateTextMediaResponse = None
_SchemaGenerateTextScriptRequest = None
_SchemaGenerateTextScriptResponse = None

try:
    from .schemas import GenerationVersionInfo as _SchemaGenerationVersionInfo  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVersionInfo = None

try:
    from .schemas import GenerationOptionsResponse as _SchemaGenerationOptionsResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationOptionsResponse = None

try:
    from .schemas import GenerationVideoModelOption as _SchemaGenerationVideoModelOption  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVideoModelOption = None

try:
    from .schemas import GenerationVideoSizeOption as _SchemaGenerationVideoSizeOption  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerationVideoSizeOption = None

try:
    from .schemas import GenerateTextMediaRequest as _SchemaGenerateTextMediaRequest  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextMediaRequest = None

try:
    from .schemas import GenerateTextMediaResponse as _SchemaGenerateTextMediaResponse  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextMediaResponse = None

try:
    from .schemas import GenerateTextScriptRequest as _SchemaGenerateTextScriptRequest  # type: ignore[attr-defined]
except Exception:
    _SchemaGenerateTextScriptRequest = None

try:
    from .schemas import GenerateTextScriptResponse as _SchemaGenerateTextScriptResponse  # type: ignore[attr-defined]
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
        stylePresets: list[dict[str, Any]] = Field(default_factory=list)
        imageSizes: list[dict[str, Any]] = Field(default_factory=list)
        videoModels: list[dict[str, Any]] = Field(default_factory=list)
        defaultVideoModel: str | None = None
        videoSizes: list[dict[str, Any]] = Field(default_factory=list)
        videoDurations: list[dict[str, Any]] = Field(default_factory=list)
        defaultVersion: int | None = None
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
        providerModel: str | None = None
        videoModel: str | None = None
        aspectRatio: str = "9:16"
        durationSeconds: float = Field(default=4.0, ge=1.0, le=30.0)
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
            self.providerModel = (self.providerModel or "").strip() or None
            self.videoModel = (self.videoModel or "").strip() or None
            self.durationSeconds = float(min(30.0, max(1.0, self.durationSeconds)))
            return self


else:
    GenerateTextMediaRequest = _SchemaGenerateTextMediaRequest


if _SchemaGenerateTextMediaResponse is None:

    class GenerateTextMediaResponse(BaseModel):
        generationId: str
        mediaType: Literal["image", "video"]
        version: str
        prompt: str
        shapedPrompt: str
        source: str
        filePath: str
        fileUrl: str
        mimeType: str
        metadata: dict[str, Any] = Field(default_factory=dict)


else:
    GenerateTextMediaResponse = _SchemaGenerateTextMediaResponse


if _SchemaGenerateTextScriptRequest is None:

    class GenerateTextScriptRequest(BaseModel):
        text: str = Field(min_length=1, max_length=50000)
        visualStyle: str | None = Field(default=None, max_length=120)

        @model_validator(mode="after")
        def _normalize(self) -> "GenerateTextScriptRequest":
            self.text = self.text.strip()
            if not self.text:
                raise ValueError("text must be non-empty")
            self.visualStyle = (self.visualStyle or "").strip() or None
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
class _VideoModelSpec:
    name: str
    label: str
    supported_sizes: tuple[str, ...]
    min_duration_seconds: int
    max_duration_seconds: int
    default_duration_seconds: int
    prompt_limit: int
    allowed_durations: tuple[int, ...] = ()

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
}

_VIDEO_MODEL_ALIASES = {
    "wan2.6-t2v-plus": "wan2.6-t2v",
    "wan2.6-t2v-turbo": "wan2.6-t2v",
    "wan2.5-t2v-plus": "wan2.5-t2v-preview",
    "wan2.5-t2v-turbo": "wan2.5-t2v-preview",
    "wan2.1-t2v-plus": "wanx2.1-t2v-plus",
    "wan2.1-t2v-turbo": "wanx2.1-t2v-turbo",
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


def _video_model_spec(model_name: str | None) -> _VideoModelSpec:
    normalized = _normalize_video_model_name(model_name)
    if normalized in _VIDEO_MODELS:
        return _VIDEO_MODELS[normalized]
    return _VIDEO_MODELS["wan2.6-i2v"]


def _video_size_profiles(spec: _VideoModelSpec) -> list[_VideoSizeProfile]:
    return [
        _VideoSizeProfile(
            label=f"{size} ({size.split('*', 1)[0]}×{size.split('*', 1)[1]})",
            width=int(size.split("*", 1)[0]),
            height=int(size.split("*", 1)[1]),
            tier="1080P" if max(int(size.split("*", 1)[0]), int(size.split("*", 1)[1])) >= 1920 else "720P" if max(int(size.split("*", 1)[0]), int(size.split("*", 1)[1])) >= 1280 else "480P",
        )
        for size in spec.supported_sizes
    ]


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


def _video_model_options(default_model_name: str | None = None) -> list[dict[str, Any]]:
    default_model_name = _normalize_video_model_name(default_model_name) or "wan2.6-i2v"
    options: list[dict[str, Any]] = []
    for spec in _VIDEO_MODELS.values():
        options.append(
            {
                "value": spec.name,
                "label": spec.label,
                "description": f"阿里云百炼官方文生视频模型 {spec.name}",
                "isDefault": spec.name == default_model_name,
                "supportedSizes": [size.replace("*", "x") for size in spec.supported_sizes],
                "supportedDurations": [item["value"] for item in _video_duration_options(spec)],
                "aliases": [alias for alias, normalized in _VIDEO_MODEL_ALIASES.items() if normalized == spec.name],
            }
        )
    return options


def _video_size_catalog() -> list[dict[str, Any]]:
    size_map: dict[str, dict[str, Any]] = {}
    for model_name, spec in _VIDEO_MODELS.items():
        for size in _video_size_options(spec):
            key = size["value"]
            entry = size_map.setdefault(
                key,
                {
                    **size,
                    "supportedModels": [],
                },
            )
            entry["supportedModels"].append(model_name)
    return sorted(size_map.values(), key=lambda item: (item["tier"], item["width"], item["height"]))


def _video_duration_catalog() -> list[dict[str, Any]]:
    duration_map: dict[int, dict[str, Any]] = {}
    for model_name, spec in _VIDEO_MODELS.items():
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
            entry["supportedModels"].append(model_name)
    return [duration_map[key] for key in sorted(duration_map)]


DEFAULT_SCRIPT_VISUAL_STYLE = "AI 自动决策"

SHORT_DRAMA_SCRIPT_SYSTEM_PROMPT = """### 🤖 AI 短剧脚本专家指令 (System Prompt)

**Role:** 你是一位资深的 AI 短剧导演和编剧，擅长将小说、散文或故事大纲转化为具备**高度视觉一致性**、**精准分镜语言**和**节奏感**的视频生产脚本。

**Task:**
根据用户输入的文本，输出一份结构化的剧本。剧本必须包含：角色档案、场景设定、分镜详细描述（含 Prompt 指令）以及音效字幕。

**Constraints:**
1. **视觉风格一致性：** 始终保持统一风格；若用户未指定，请根据题材、情绪和场景自行决策最合适的视觉方向，并在全片保持一致。
2. **角色锚点：** 为每个角色建立固定的外貌描述词，确保在每个分镜中一致。
3. **分镜语言：** 使用专业术语（全景、特写、俯拍、推拉摇移）。
4. **输出格式：** 使用 Markdown 表格。

#### **工作流程：**

**第一步：角色与环境档案 (Profile)**
- 提取文中所有核心角色，定义其：姓名、年龄、具体长相（发型、瞳色、服装）、性格特征。
- 定义核心场景的视觉基调（如：午后阳光下的教室、阴冷的古堡室内）。

**第二步：脚本生成 (Script)**
生成包含以下列的表格：
- **镜号**
- **景别/镜头运动** (如：特写/推镜头)
- **视觉描述 (AI 绘图 Prompt)**：必须包含角色名、具体动作、环境细节、光影氛围。
- **对话/旁白**
- **音效/BGM 建议**

#### **输出示例格式：**

**【角色档案】**
* **角色 A：** [姓名]，[外貌细节描述]，[核心标签]。

**【分镜脚本】**
| 镜号 | 景别 | 视觉描述 (Visual Prompt) | 对话/字幕 | 建议时长 |
| :--- | :--- | :--- | :--- | :--- |
| 001 | 远景 | 晨曦照进森林，光点在草地上跳跃，日系手绘感，清新明亮。 | (旁白) 故事开始于那个清晨。 | 4s |
| 002 | 特写 | [角色名] 睁开眼，淡褐色双眸，长发散乱，露出惊讶的神色。 | “这...这是哪里？” | 3s |

请根据用户给出的正文直接产出最终脚本，不要输出额外解释。"""


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

    def list_versions(self) -> GenerationOptionsResponse:
        return self.get_generation_options()

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
        default_video_spec = self._resolve_video_model_spec()
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
                "videoModels": _video_model_options(default_video_spec.name),
                "videoSizes": _video_size_catalog(),
                "videoDurations": _video_duration_catalog(),
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

    def generate_text_image(self, payload: Any) -> GenerateTextMediaResponse:
        request_obj = self._normalize_request(payload, default_kind="image")
        return self._generate_media("image", request_obj)

    def generate_text_video(self, payload: Any) -> GenerateTextMediaResponse:
        request_obj = self._normalize_request(payload, default_kind="video")
        return self._generate_media("video", request_obj)

    def generate_text_script(self, payload: Any) -> GenerateTextScriptResponse:
        request_obj = self._normalize_script_request(payload)
        return self._generate_script(request_obj)

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
        if normalized.get("videoModel") and not normalized.get("providerModel"):
            normalized["providerModel"] = normalized["videoModel"]
        if normalized.get("providerModel") and not normalized.get("videoModel"):
            normalized["videoModel"] = normalized["providerModel"]
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
        if video_size and ("width" not in normalized or "height" not in normalized):
            try:
                width, height = self._parse_video_size(video_size)
                normalized.setdefault("width", width)
                normalized.setdefault("height", height)
            except Exception:
                pass
        if "width" not in normalized or "height" not in normalized:
            ratio = str(normalized.get("aspectRatio", "9:16")).strip()
            width, height = self._resolution_for_aspect_ratio(ratio)
            normalized.setdefault("width", width)
            normalized.setdefault("height", height)

        if default_kind == "image":
            normalized.pop("durationSeconds", None)
        else:
            if normalized.get("durationSeconds") in {None, ""}:
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
        if hasattr(GenerateTextScriptRequest, "model_validate"):
            return GenerateTextScriptRequest.model_validate(payload)  # type: ignore[attr-defined]
        return GenerateTextScriptRequest(**payload)

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
        shaped_prompt = self._shape_prompt(media_type, prompt, profile, extras)
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
                "shapedPromptLength": len(shaped_prompt),
            },
        )

        provider_endpoint = self._resolve_video_endpoint() if media_type == "video" else str(self.settings.model.endpoint).strip()
        if not provider_endpoint or not self.settings.model.api_key:
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
                remote_result = self._generate_dashscope_video(
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
        model_name = self._resolve_video_model_spec(request_obj).name if media_type == "video" else self.settings.model.model_name
        provider_name = "aliyun-bailian" if media_type == "video" else self.settings.model.provider
        task_endpoint_host = ""
        if media_type == "video":
            try:
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
                "modelInfo": {
                    "provider": provider_name,
                    "modelName": model_name,
                    "providerModel": model_name if media_type == "video" else None,
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

    def _generate_script(self, request_obj: GenerateTextScriptRequest) -> GenerateTextScriptResponse:
        call_chain: list[dict[str, Any]] = []
        generation_id = new_id("script")
        source_text = str(getattr(request_obj, "text", "")).strip()
        requested_visual_style = str(getattr(request_obj, "visualStyle", "") or "").strip()
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
            },
        )

        endpoint = str(self.settings.model.endpoint).strip()
        if not endpoint or not self.settings.model.api_key:
            self._trace_call(
                call_chain,
                stage="provider",
                event="config",
                status="error",
                message="provider config missing",
            )
            raise RuntimeError("text script provider is not configured")

        user_prompt = (
            "请基于下面的正文生成一份可直接用于短剧生产的 Markdown 脚本。\n"
            f"{'用户指定视觉风格：' + visual_style if requested_visual_style else '视觉风格：请你根据题材与情绪自动决策，并在全片保持统一。'}\n"
            "如果原文信息不完整，请在不偏离原意的前提下补足角色外观锚点、环境视觉基调和分镜动作。\n"
            "请直接输出最终剧本，不要写解释、前言或额外说明。\n\n"
            "【用户正文开始】\n"
            f"{source_text}\n"
            "【用户正文结束】"
        )
        body = {
            "model": self.settings.model.model_name,
            "messages": [
                {"role": "system", "content": SHORT_DRAMA_SCRIPT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": min(0.45, max(0.12, self.settings.model.temperature + 0.05)),
            "max_tokens": min(3200, self.settings.model.max_tokens),
        }
        request = urllib.request.Request(
            endpoint,
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
            message="remote script generation request sent",
            details={
                "modelName": self.settings.model.model_name,
                "provider": self.settings.model.provider,
                "temperature": body["temperature"],
                "maxTokens": body["max_tokens"],
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
                message="remote script generation response received",
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
                message="remote script generation timeout",
                details={"error": str(exc)},
            )
            raise RuntimeError(f"remote script generation timeout: {exc}") from exc
        except urllib.error.HTTPError as exc:
            self._trace_call(
                call_chain,
                stage="remote_response",
                event="received",
                status="error",
                message="remote script generation http error",
                details={"statusCode": int(exc.code)},
            )
            raise RuntimeError(f"remote script generation http error: {exc.code}") from exc
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
                "source": f"remote:{self.settings.model.model_name}",
                "createdAt": created_at,
                "modelInfo": {
                    "provider": self.settings.model.provider,
                    "modelName": self.settings.model.model_name,
                    "endpointHost": endpoint_host,
                    "temperature": body["temperature"],
                    "maxTokens": body["max_tokens"],
                    "timeoutSeconds": self.settings.model.timeout_seconds,
                },
                "callChain": call_chain,
                "metadata": {
                    "systemPromptName": "ai-short-drama-script-expert",
                    "visualStyle": visual_style,
                    "sourceTextLength": len(source_text),
                    "outputFormat": "markdown",
                    "markdownFilePath": relative_markdown_path,
                    "markdownFileUrl": markdown_url,
                    "rawTopLevelKeys": list(payload.keys())[:12],
                },
            },
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

        endpoint = str(self.settings.model.endpoint).strip()
        if not endpoint:
            raise RuntimeError("model endpoint is empty")
        if not self.settings.model.api_key:
            raise RuntimeError("model api_key is empty")

        width, height = self._resolve_dimensions(request_obj)
        duration_seconds = float(getattr(request_obj, "durationSeconds", 0.0) or 0.0)
        aspect_ratio = self._aspect_ratio_label(width, height)
        body = {
            "model": self.settings.model.model_name,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {
                    "role": "user",
                    "content": (
                        f"Task: generate {media_type} from text.\n"
                        f"Version profile: {profile.version} ({profile.name})\n"
                        f"Aspect ratio: {aspect_ratio}\n"
                        f"Resolution: {width}x{height}\n"
                        f"Duration seconds: {duration_seconds:.2f}\n"
                        f"Prompt: {shaped_prompt}\n"
                        'Output JSON: {"file_url":"https://...", "base64_data":"...", "mime_type":"image/png or video/mp4"}'
                    ),
                },
            ],
            "temperature": min(0.35, max(0.05, self.settings.model.temperature)),
            "max_tokens": min(900, self.settings.model.max_tokens),
        }

        request = urllib.request.Request(
            endpoint,
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
                "modelName": self.settings.model.model_name,
                "provider": self.settings.model.provider,
                "kind": media_type,
                "temperature": body["temperature"],
                "maxTokens": body["max_tokens"],
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
        width, height = self._resolve_dimensions(request_obj)
        normalized_width, normalized_height, normalized_size = self._normalize_video_size(
            spec=spec,
            width=width,
            height=height,
        )
        normalized_duration = self._normalize_video_duration(
            spec=spec,
            requested=float(getattr(request_obj, "durationSeconds", spec.default_duration_seconds) or spec.default_duration_seconds),
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

        requested_duration = float(getattr(request_obj, "durationSeconds", 0.0) or 0.0)
        if requested_duration and abs(requested_duration - normalized_duration) > 0.01:
            self._trace_call(
                call_chain,
                stage="request",
                event="normalize_duration",
                status="ok",
                message="video duration adjusted to provider-supported range",
                details={
                    "requested": requested_duration,
                    "normalized": normalized_duration,
                    "modelName": spec.name,
                },
            )

        prompt = shaped_prompt.strip()
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
            "model": spec.name,
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
                "provider": "aliyun-bailian",
                "size": normalized_size,
                "durationSeconds": int(normalized_duration),
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
                "taskId": task_id,
                "requestId": request_id,
                "providerModel": spec.name,
                "taskStatus": str(output_block.get("task_status") or output_block.get("taskStatus") or "SUCCEEDED"),
                "submitTime": output_block.get("submit_time"),
                "scheduledTime": output_block.get("scheduled_time"),
                "endTime": output_block.get("end_time"),
                "stylePreset": getattr(request_obj, "stylePreset", None),
                "actualPrompt": remote_prompt,
                "modelInfo": {
                    "provider": "aliyun-bailian",
                    "modelName": spec.name,
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

    def _parse_json_bytes(self, raw: bytes) -> dict[str, Any]:
        text = raw.decode("utf-8", errors="ignore").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except Exception:
            return {}

    def _extract_media_blob(
        self,
        *,
        media_type: Literal["image", "video"],
        payload: dict[str, Any],
        raw_text: str,
        call_chain: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        download_errors: list[str] = []

        def _try_download(url: str) -> dict[str, Any] | None:
            try:
                data, mime_type = self._download_binary(url, call_chain=call_chain)
                return {"data": data, "mimeType": mime_type, "sourceUrl": url}
            except Exception as exc:
                download_errors.append(str(exc))
                return None

        if isinstance(payload.get("data"), list) and payload["data"]:
            first = payload["data"][0]
            if isinstance(first, dict):
                url = self._first_str(first, ("url", "file_url", "fileUrl", "media_url", "mediaUrl"))
                if url:
                    self._trace_call(
                        call_chain,
                        stage="media_extract",
                        event="candidate_url",
                        status="ok",
                        message="found media url in data[0]",
                        details={"url": url[:240]},
                    )
                    downloaded = _try_download(url)
                    if downloaded is not None:
                        return downloaded
                b64 = self._first_str(first, ("b64_json", "base64", "base64_data", "base64Data", "data"))
                if b64:
                    self._trace_call(
                        call_chain,
                        stage="media_extract",
                        event="base64",
                        status="ok",
                        message="using base64 payload from data[0]",
                    )
                    data = self._decode_base64_blob(b64)
                    mime_type = self._first_str(first, ("mime_type", "mimeType")) or ""
                    return {"data": data, "mimeType": mime_type, "sourceUrl": ""}

        model_json = self._extract_json_from_model_payload(payload, raw_text)
        url = self._first_str(
            model_json,
            ("url", "file_url", "fileUrl", "media_url", "mediaUrl", "download_url", "downloadUrl"),
        )
        if url:
            self._trace_call(
                call_chain,
                stage="media_extract",
                event="candidate_url",
                status="ok",
                message="found media url in model json",
                details={"url": url[:240]},
            )
            downloaded = _try_download(url)
            if downloaded is not None:
                return downloaded

        b64 = self._first_str(model_json, ("b64_json", "base64", "base64_data", "base64Data", "data"))
        if b64:
            self._trace_call(
                call_chain,
                stage="media_extract",
                event="base64",
                status="ok",
                message="using base64 payload from model json",
            )
            mime_type = self._first_str(model_json, ("mime_type", "mimeType")) or ""
            data = self._decode_base64_blob(b64)
            return {"data": data, "mimeType": mime_type, "sourceUrl": ""}

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
        candidates: list[str] = []

        if isinstance(payload.get("choices"), list):
            for choice in payload["choices"]:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message")
                if isinstance(message, dict):
                    candidates.extend(self._collect_text_chunks(message.get("content")))
                candidates.extend(self._collect_text_chunks(choice.get("text")))

        candidates.extend(self._collect_text_chunks(payload.get("output_text")))

        output = payload.get("output")
        if isinstance(output, (dict, list, str)):
            candidates.extend(self._collect_text_chunks(output))

        if isinstance(payload.get("message"), dict):
            candidates.extend(self._collect_text_chunks(payload["message"].get("content")))

        for candidate in candidates:
            normalized = candidate.strip()
            if normalized:
                return normalized
        return raw_text.strip()

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
        path, drawtext_applied = self._generate_local_video(request_obj, profile, shaped_prompt, generation_id)
        return {
            "path": path,
            "mimeType": "video/mp4",
            "metadata": {
                "byteSize": path.stat().st_size,
                "engine": "local-ffmpeg",
                "drawtextApplied": drawtext_applied,
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
            f'<text x="{int(width * 0.1)}" y="{int(height * 0.1)}" font-family="Arial, sans-serif" font-size="{int(height * 0.028)}" fill="white" fill-opacity="0.75">{html_escape(profile.version.upper())} | {html_escape(profile.name)}</text>',
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
    ) -> tuple[Path, bool]:
        width, height = self._resolve_dimensions(request_obj)
        duration = float(getattr(request_obj, "durationSeconds", 4.0))
        safe_duration = max(1.0, min(30.0, duration))
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
            return output_path, True
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
            return output_path, False

    def _run_command(self, command: list[str]) -> None:
        try:
            completed = subprocess.run(command, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"{command[0]} is not installed or not available in PATH") from exc
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "command failed"
            raise RuntimeError(stderr)

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
                f"[{profile.version}] {profile.image_prompt_style}",
                f"Subject: {subject}.",
            ]
            if style_hint:
                parts.append(f"Additional style: {style_hint}.")
            if lighting_hint:
                parts.append(f"Lighting: {lighting_hint}.")
            parts.append("Deliver a single coherent frame with clear focal hierarchy.")
            return " ".join(parts)

        parts = [
            f"[{profile.version}] {profile.video_prompt_style}",
            f"Core concept: {subject}.",
        ]
        if style_hint:
            parts.append(f"Visual style: {style_hint}.")
        if camera_hint:
            parts.append(f"Camera direction: {camera_hint}.")
        if lighting_hint:
            parts.append(f"Lighting direction: {lighting_hint}.")
        parts.append("Deliver one short shot concept with beginning, motion beat, and end beat.")
        return " ".join(parts)

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
        duration_seconds = float(getattr(request_obj, "durationSeconds", 0.0) or 0.0) if media_type == "video" else None
        version_int = int(version.lstrip("v") or "1")
        enriched_metadata = dict(metadata)
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

    def _normalize_video_duration(self, *, spec: _VideoModelSpec, requested: float) -> int:
        if spec.is_fixed_duration:
            return spec.default_duration_seconds
        rounded = int(round(requested or spec.default_duration_seconds))
        if spec.allowed_durations:
            return min(spec.allowed_durations, key=lambda value: abs(value - rounded))
        return min(spec.max_duration_seconds, max(spec.min_duration_seconds, rounded))

    def _parse_video_size(self, value: str) -> tuple[int, int]:
        normalized = value.replace("x", "*").replace("X", "*")
        width_raw, _, height_raw = normalized.partition("*")
        return max(1, int(width_raw)), max(1, int(height_raw))

    def _extract_video_url(self, payload: dict[str, Any]) -> str:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        direct_url = self._first_str(output, ("video_url", "videoUrl", "url", "file_url", "fileUrl"))
        if direct_url:
            return direct_url
        results = output.get("results")
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                url = self._first_str(item, ("video_url", "videoUrl", "url", "file_url", "fileUrl"))
                if url:
                    return url
        return ""

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
