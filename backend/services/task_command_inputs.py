"""Pure validation, normalization, and retry policy for task commands."""

from __future__ import annotations

from typing import Any

from backend.domain.enums import AttemptTriggerType
from backend.domain.task_record import TaskRecord
from backend.domain.task_resume import existing_video_clip_indices, last_contiguous_completed_clip_index


def trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    normalized = value.strip()
    return normalized or fallback


def require_selected_model(value: str | None, field_name: str, label: str) -> str:
    normalized = trimmed(value, "")
    if normalized:
        return normalized
    raise ValueError(f"Please select {label} ({field_name})")


def normalize_task_type(
    value: str | None,
    reference_image_urls: list[str] | None,
    asset_type: str | None,
) -> str:
    normalized = trimmed(value, "")
    if not normalized or normalized == "generation":
        if normalized_asset_type(asset_type, "") == "character_sheet":
            return "character_sheet"
        return "image_to_image" if normalize_string_list(reference_image_urls) else "video_generation"
    return normalized


def credit_feature_code(task_type: str | None) -> str:
    normalized = trimmed(task_type, "")
    if normalized == "video_generation":
        return "VIDEO_GENERATION"
    if normalized in {"image_generation", "image_to_image", "character_sheet"}:
        return "IMAGE_GENERATION"
    return ""


def normalized_asset_type(asset_type: str | None, task_type: str) -> str:
    return trimmed(asset_type, "") or (
        "character_sheet" if task_type == "character_sheet" else "free"
    )


def normalize_string_list(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        normalized = trimmed(value, "")
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def normalize_optional_seed(seed: int | None) -> int | None:
    if seed is not None and seed < 0:
        raise ValueError("seed must be >= 0")
    return seed


def normalize_output_count(value: Any) -> dict[str, Any]:
    if value is None or value == "" or (
        isinstance(value, str) and value.strip().lower() == "auto"
    ):
        return {"auto": True}
    if isinstance(value, dict):
        if value.get("auto"):
            return {"auto": True}
        value = value.get("count")
    try:
        count = int(value)
    except (TypeError, ValueError):
        return {"auto": True}
    return {"auto": False, "count": max(1, count)}


def normalize_effect_rating(rating: int | None) -> int:
    if rating is None:
        raise ValueError("effectRating must not be None")
    if rating < 1 or rating > 5:
        raise ValueError("effectRating must be between 1 and 5")
    return rating


def normalize_effect_rating_note(note: str | None) -> str:
    normalized = trimmed(note, "")
    if len(normalized) > 1000:
        raise ValueError("effectRatingNote must not exceed 1000 characters")
    return normalized


def build_retry_payload(task: TaskRecord, trigger_type: AttemptTriggerType) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "triggerType": trigger_type.value,
        "retryCount": task.retry_count,
    }
    clip_indices = existing_video_clip_indices(task.outputs_view)
    completed_clip_count = last_contiguous_completed_clip_index(clip_indices)
    if task.storyboard_script:
        payload.update(
            resumeFromStage="render" if completed_clip_count > 0 else "planning",
            resumeFromClipIndex=max(1, completed_clip_count + 1),
            completedClipCount=completed_clip_count,
            existingClipIndices=clip_indices,
            reuseStoryboard=True,
        )
    return payload
