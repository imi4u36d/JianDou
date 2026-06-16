"""Generation request snapshot — immutable record of the original task request.

Mirrors the Java GenerationRequestSnapshot domain record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RequestedDuration:
    """Duration parameter: auto or explicit seconds."""

    auto: bool
    seconds: int | None = None

    @classmethod
    def automatic(cls) -> RequestedDuration:
        return cls(auto=True, seconds=None)

    @classmethod
    def from_raw(cls, raw: object) -> RequestedDuration:
        if raw is None:
            return cls.automatic()
        if isinstance(raw, (int, float)):
            return cls(auto=False, seconds=max(1, int(raw)))
        value = str(raw).strip()
        if not value or value.lower() == "auto":
            return cls.automatic()
        try:
            return cls(auto=False, seconds=max(1, round(float(value))))
        except (ValueError, TypeError):
            return cls.automatic()

    def to_value(self) -> object:
        return "auto" if self.auto else self.seconds


@dataclass(frozen=True)
class RequestedOutputCount:
    """Output count parameter: auto or explicit count."""

    auto: bool
    count: int | None = None

    @classmethod
    def automatic(cls) -> RequestedOutputCount:
        return cls(auto=True, count=None)

    @classmethod
    def from_raw(cls, raw: object) -> RequestedOutputCount:
        if raw is None:
            return cls.automatic()
        if isinstance(raw, (int, float)):
            return cls(auto=False, count=max(1, int(raw)))
        value = str(raw).strip()
        if not value or value.lower() == "auto":
            return cls.automatic()
        try:
            return cls(auto=False, count=max(1, int(value)))
        except (ValueError, TypeError):
            return cls.automatic()

    def to_value(self) -> object:
        return "auto" if self.auto else self.count


@dataclass(frozen=True)
class GenerationRequestSnapshot:
    """Immutable snapshot of the generation request at task creation time.

    Mirrors the Java GenerationRequestSnapshot record.
    """

    task_type: str = "generation"
    asset_type: str = ""
    title: str = ""
    creative_prompt: str = ""
    aspect_ratio: str = ""
    image_size: str = ""
    style_preset: str = "cinematic"
    text_analysis_model: str = ""
    image_model: str = ""
    video_model: str = ""
    video_size: str = ""
    seed: int | None = None
    video_duration: RequestedDuration = field(default_factory=RequestedDuration.automatic)
    output_count: RequestedOutputCount = field(default_factory=RequestedOutputCount.automatic)
    min_duration_seconds: int = 0
    max_duration_seconds: int = 0
    transcript_text: str = ""
    stop_before_video_generation: bool = False

    @classmethod
    def empty(cls) -> GenerationRequestSnapshot:
        return cls(
            task_type="generation",
            asset_type="",
            title="",
            creative_prompt="",
            aspect_ratio="",
            image_size="",
            style_preset="cinematic",
            text_analysis_model="",
            image_model="",
            video_model="",
            video_size="",
            seed=None,
            video_duration=RequestedDuration.automatic(),
            output_count=RequestedOutputCount.automatic(),
            min_duration_seconds=0,
            max_duration_seconds=0,
            transcript_text="",
            stop_before_video_generation=False,
        )

    @classmethod
    def from_map(cls, data: dict[str, Any] | None) -> GenerationRequestSnapshot:
        if not data:
            return cls.empty()
        return cls(
            task_type=_string_value(data.get("taskType"), "generation"),
            asset_type=_string_value(data.get("assetType"), ""),
            title=_string_value(data.get("title"), ""),
            creative_prompt=_string_value(data.get("creativePrompt"), ""),
            aspect_ratio=_string_value(data.get("aspectRatio"), ""),
            image_size=_string_value(data.get("imageSize"), ""),
            style_preset=_string_value(data.get("stylePreset"), "cinematic"),
            text_analysis_model=_string_value(data.get("textAnalysisModel"), ""),
            image_model=_string_value(data.get("imageModel"), ""),
            video_model=_string_value(data.get("videoModel"), ""),
            video_size=_string_value(data.get("videoSize"), ""),
            seed=_integer_value(data.get("seed")),
            video_duration=RequestedDuration.from_raw(data.get("videoDurationSeconds")),
            output_count=RequestedOutputCount.from_raw(data.get("outputCount")),
            min_duration_seconds=_integer_value(data.get("minDurationSeconds"), 0),
            max_duration_seconds=_integer_value(data.get("maxDurationSeconds"), 0),
            transcript_text=_string_value(data.get("transcriptText"), ""),
            stop_before_video_generation=_boolean_value(data.get("stopBeforeVideoGeneration")),
        )

    def to_map(self) -> dict[str, Any]:
        return {
            "taskType": self.task_type,
            "assetType": self.asset_type,
            "title": self.title,
            "creativePrompt": self.creative_prompt,
            "aspectRatio": self.aspect_ratio,
            "imageSize": self.image_size,
            "stylePreset": self.style_preset,
            "textAnalysisModel": self.text_analysis_model,
            "imageModel": self.image_model,
            "videoModel": self.video_model,
            "videoSize": self.video_size,
            "seed": self.seed,
            "videoDurationSeconds": self.video_duration.to_value(),
            "outputCount": self.output_count.to_value(),
            "minDurationSeconds": self.min_duration_seconds,
            "maxDurationSeconds": self.max_duration_seconds,
            "transcriptText": self.transcript_text,
            "stopBeforeVideoGeneration": self.stop_before_video_generation,
        }

    def model_value(self, field_name: str) -> str:
        """Get the model value for a given field name."""
        return {
            "textAnalysisModel": self.text_analysis_model,
            "imageModel": self.image_model,
            "videoModel": self.video_model,
        }.get(field_name, "")


def _string_value(value: object, fallback: str = "") -> str:
    normalized = "" if value is None else str(value).strip()
    return normalized if normalized else fallback


def _integer_value(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _integer_value(value: object, fallback: int) -> int:
    parsed = _integer_value(value)
    return fallback if parsed is None else parsed


def _boolean_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None and str(value).strip().lower() in ("true", "1", "yes")
