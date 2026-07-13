"""Immutable task request snapshot construction."""

from __future__ import annotations

from typing import Any

from backend.domain.request_snapshot import GenerationRequestSnapshot, RequestedDuration, RequestedOutputCount
from backend.shared import first_non_blank, string_value


def _int_value(value: object, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    normalized = value.strip()
    return normalized if normalized else fallback


class TaskRequestSnapshotFactory:
    """Creates immutable snapshots of generation requests at task creation time.

    Mirrors the Java TaskRequestSnapshotFactory application component.
    """

    def __init__(self, model_resolver: Any) -> None:
        self._model_resolver = model_resolver

    def create(self, request: Any, task: Any) -> GenerationRequestSnapshot:
        """Build a GenerationRequestSnapshot from a request and task record."""
        task_type = self._normalized_task_type(
            string_value(task.task_type if task is not None else ""),
            string_value(getattr(request, "task_type", None) if hasattr(request, "task_type") else
                          getattr(request, "taskType", None)),
        )

        return GenerationRequestSnapshot(
            task_type=task_type,
            asset_type=self._normalized_asset_type(
                string_value(getattr(request, "asset_type", None) if hasattr(request, "asset_type") else
                              getattr(request, "assetType", None)),
                task_type,
            ),
            title=string_value(getattr(task, "title", "")),
            creative_prompt=string_value(getattr(task, "creative_prompt", getattr(task, "creativePrompt", ""))),
            aspect_ratio=string_value(getattr(task, "aspect_ratio", getattr(task, "aspectRatio", ""))),
            image_size=_trimmed(
                getattr(request, "image_size", None) if hasattr(request, "image_size") else
                getattr(request, "imageSize", None),
                "",
            ),
            text_analysis_model=_trimmed(
                getattr(request, "text_analysis_model", None) if hasattr(request, "text_analysis_model") else
                getattr(request, "textAnalysisModel", None),
                "",
            ),
            image_model=_trimmed(
                getattr(request, "image_model", None) if hasattr(request, "image_model") else
                getattr(request, "imageModel", None),
                "",
            ),
            video_model=_trimmed(
                getattr(request, "video_model", None) if hasattr(request, "video_model") else
                getattr(request, "videoModel", None),
                "",
            ),
            video_size=_trimmed(
                getattr(request, "video_size", None) if hasattr(request, "video_size") else
                getattr(request, "videoSize", None),
                self._model_resolver_value("catalog.defaults", "video_size", "720*1280"),
            ),
            seed=getattr(task, "task_seed", getattr(task, "taskSeed", None)),
            video_duration=RequestedDuration.from_raw(
                getattr(request, "video_duration_seconds", None) if hasattr(request, "video_duration_seconds") else
                getattr(request, "videoDurationSeconds", None),
            ),
            output_count=RequestedOutputCount.from_raw(
                self._normalize_output_count(
                    getattr(request, "output_count", None) if hasattr(request, "output_count") else
                    getattr(request, "outputCount", None),
                ),
            ),
            min_duration_seconds=_int_value(getattr(task, "min_duration_seconds", getattr(task, "minDurationSeconds", 0)), 0),
            max_duration_seconds=_int_value(getattr(task, "max_duration_seconds", getattr(task, "maxDurationSeconds", 0)), 0),
            transcript_text=string_value(getattr(task, "transcript_text", getattr(task, "transcriptText", ""))),
            stop_before_video_generation=bool(
                getattr(request, "stop_before_video_generation", None) if hasattr(request, "stop_before_video_generation") else
                getattr(request, "stopBeforeVideoGeneration", None) or False
            ),
        )

    def request_snapshot_output_count(self, task: Any) -> int:
        """Return the resolved output count from a task's request snapshot."""
        snapshot = getattr(task, "request_snapshot", None) or {}
        raw = snapshot.get("outputCount") if isinstance(snapshot, dict) else None
        if raw is None:
            return 1
        if isinstance(raw, (int, float)):
            return max(1, int(raw))
        return 1

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _model_resolver_value(self, section: str, key: str, fallback: str) -> str:
        if self._model_resolver is not None and hasattr(self._model_resolver, "value"):
            try:
                result = self._model_resolver.value(section, key, fallback)
                if result is not None:
                    return string_value(result)
            except Exception:  # noqa: S110 — best-effort config resolution
                pass
        return fallback

    @staticmethod
    def _normalized_task_type(task_value: str, request_value: str) -> str:
        normalized = first_non_blank(request_value, task_value, "generation")
        if not request_value and normalized == "video_generation":
            return "generation"
        valid = {"image_generation", "image_to_image", "character_sheet", "video_generation", "generation"}
        if normalized in valid:
            return normalized
        return normalized

    @staticmethod
    def _normalized_asset_type(asset_type: str, task_type: str) -> str:
        if asset_type:
            return asset_type
        return "character_sheet" if task_type == "character_sheet" else "free"

    @staticmethod
    def _normalize_output_count(output_count: object) -> object:
        if output_count is None:
            return "auto"
        raw = string_value(output_count)
        if not raw or raw.lower() == "auto":
            return "auto"
        try:
            value = int(raw)
            if value < 1:
                raise ValueError("outputCount must be greater than 0")
            return value
        except (ValueError, TypeError) as ex:
            if isinstance(ex, ValueError) and "must be greater than 0" in str(ex):
                raise
            raise ValueError("outputCount must be a positive integer or 'auto'")
