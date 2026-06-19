"""Task artifact naming utility — generates names and paths for task outputs.

Mirrors the Java TaskArtifactNaming domain class.
All methods are stateless module-level functions.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def task_artifact_relative_dir(task: Any) -> str:
    """Relative directory for all task artifacts."""
    return _task_artifact_base_relative_dir(task)


def task_base_relative_dir(task: Any) -> str:
    """Base relative directory for task artifacts (no subfolder)."""
    return _task_artifact_base_relative_dir(task)


def task_running_relative_dir(task: Any) -> str:
    """Relative directory for running (unjoined) task clips."""
    return _task_artifact_base_relative_dir(task) + "/running"


def task_joined_relative_dir(task: Any) -> str:
    """Relative directory for joined task outputs."""
    return _task_artifact_base_relative_dir(task) + "/joined"


def storyboard_file_name(task: Any, extension: str) -> str:
    """File name for the storyboard."""
    return "storyboard." + _normalize_extension(extension)


def keyframe_file_name(task: Any, clip_index: int, extension: str) -> str:
    """File name for a keyframe (first frame of a clip)."""
    return _clip_frame_file_name(clip_index, "first", extension)


def last_frame_file_name(clip_index: int, extension: str) -> str:
    """File name for the last frame of a clip."""
    return _clip_frame_file_name(clip_index, "last", extension)


def clip_frame_file_name(clip_index: int, frame_role: str, extension: str) -> str:
    """File name for a specific frame of a clip."""
    resolved_role = _normalize_frame_role(frame_role)
    resolved_extension = _normalize_extension(extension)
    return f"clip{_normalized_clip_index(clip_index)}-{resolved_role}.{resolved_extension}"


def clip_file_name(clip_index: int, extension: str) -> str:
    """File name for a clip (video/image)."""
    resolved_extension = _normalize_extension(extension)
    return f"clip{_normalized_clip_index(clip_index)}.{resolved_extension}"


def join_file_name(end_clip_index: int, extension: str) -> str:
    """File name for the join output."""
    return _join_name(end_clip_index) + "." + _normalize_extension(extension)


def join_name(end_clip_index: int) -> str:
    """Base name for the join output (e.g. join-1-2-3)."""
    parts = ["join"]
    for index in range(1, max(2, end_clip_index) + 1):
        parts.append(str(index))
    return "-".join(parts)


def _task_artifact_base_relative_dir(task: Any) -> str:
    date = _resolve_task_date(task)
    return (
        f"gen/"
        f"{date.year}-{_two_digit(date.month)}-{_two_digit(date.day)}"
        f"/"
        f"{_safe_task_directory(task.id if task is not None else None)}"
    )


def _clip_frame_file_name(clip_index: int, frame_role: str, extension: str) -> str:
    resolved_role = _normalize_frame_role(frame_role)
    resolved_extension = _normalize_extension(extension)
    return f"clip{_normalized_clip_index(clip_index)}-{resolved_role}.{resolved_extension}"


def _join_name(end_clip_index: int) -> str:
    parts = ["join"]
    limit = max(2, end_clip_index)
    for index in range(1, limit + 1):
        parts.append(str(index))
    return "-".join(parts)


def _resolve_task_date(task: Any) -> "datetime":
    """Resolve the task creation date, falling back to UTC now."""
    created_at_str: str = ""
    if task is not None:
        created_at_str = _string_value(getattr(task, "created_at", None) if hasattr(task, "created_at") else "")
    if created_at_str:
        try:
            if "T" in created_at_str:
                return datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).date()
            return datetime.fromisoformat(created_at_str).date()
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc).date()


def _safe_task_directory(task_id: str | None) -> str:
    normalized = _string_value(task_id).replace("\\", "_").replace("/", "_").strip()
    return normalized if normalized else "task-unknown"


def _normalize_segment(value: str, fallback: str) -> str:
    normalized = _string_value(value)
    normalized = re.sub(r"[^\w-]+", "_", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[^\w\-_]+", "_", normalized, flags=re.UNICODE)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    normalized = re.sub(r"^[_-]+", "", normalized)
    normalized = re.sub(r"[_-]+$", "", normalized)
    return normalized if normalized else fallback


def _normalize_extension(extension: str) -> str:
    normalized = _string_value(extension).replace(".", "").strip().lower()
    return normalized if normalized else "bin"


def _normalize_frame_role(frame_role: str) -> str:
    normalized = _normalize_segment(frame_role, "first").lower()
    return "last" if normalized == "last" else "first"


def _normalized_clip_index(clip_index: int) -> int:
    return max(1, clip_index)


def _two_digit(value: int) -> str:
    return f"{value:02d}"


def _string_value(value: Any) -> str:
    return "" if value is None else str(value).strip()
