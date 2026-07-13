"""Pure filtering and ordering policy for task read models."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import string_value


def task_type_set(value: str | None) -> set[str]:
    return {item.strip() for item in string_value(value).split(",") if item.strip()}


def task_comparator(sort: str | None) -> Callable[[TaskRecord], Any]:
    normalized = string_value(sort).strip().lower() or "created_desc"

    def sort_key(task: TaskRecord) -> Any:
        if normalized == "created_desc":
            return (-_timestamp(task.created_at), string_value(task.id))
        if normalized == "progress_desc":
            return (-task.progress, -_timestamp(task.updated_at), string_value(task.id))
        if normalized == "semantic_desc":
            score = 1 if task.has_timed_transcript or task.has_transcript else 0
            return (-score, -_timestamp(task.updated_at), string_value(task.id))
        if normalized == "status_desc":
            return (0, string_value(task.status), -_timestamp(task.updated_at), string_value(task.id))
        if normalized in ("effect_rating_desc", "rating_desc"):
            rating = task.effect_rating if task.effect_rating is not None else float("-inf")
            return (-rating, -_timestamp(task.updated_at), string_value(task.id))
        return (-_timestamp(task.updated_at), string_value(task.id))

    return lambda task: (sort_key(task),)


def showcase_comparator() -> Callable[[TaskRecord], Any]:
    def sort_key(task: TaskRecord) -> Any:
        rating = task.effect_rating if task.effect_rating is not None else float("-inf")
        return (-rating, -task.completed_output_count, string_value(task.updated_at))

    return sort_key


def matches_task_status(task: TaskRecord, status_filter: str | None) -> bool:
    if not status_filter:
        return True
    normalized = status_filter.strip().upper()
    if normalized == "QUEUED":
        return task.is_queued
    if normalized == "ACTIVE":
        return task.status in ("PENDING", "ANALYZING", "PLANNING", "RENDERING", "PAUSED")
    if normalized == "PENDING":
        return task.status == "PENDING"
    return task.status == normalized


def _timestamp(value: str | None) -> float:
    text = string_value(value).strip()
    if not text:
        return 0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0
