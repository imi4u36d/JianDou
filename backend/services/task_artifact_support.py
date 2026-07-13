"""Shared naming, coercion, and identity helpers for task artifacts."""

from __future__ import annotations

import uuid
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import string_value


def _int_value(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _float_value(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return string_value(value).lower() in ("true", "1", "yes")


def _stable_id(prefix: str, *parts: str) -> str:
    seed = prefix + ":" + ":".join(parts)
    return prefix + "_" + uuid.uuid5(uuid.NAMESPACE_OID, seed).hex


_JOIN_OUTPUT_CLIP_INDEX_BASE = 10000


class _TaskArtifactNaming:
    @staticmethod
    def task_base_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}"

    @staticmethod
    def task_running_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/running"

    @staticmethod
    def task_joined_relative_dir(task: TaskRecord) -> str:
        return f"tasks/{task.id}/joined"

    @staticmethod
    def storyboard_file_name(task: TaskRecord, ext: str) -> str:
        return f"storyboard-{task.id}.{ext}"

    @staticmethod
    def clip_frame_file_name(clip_index: int, frame_role: str, ext: str) -> str:
        return f"clip{clip_index}-{frame_role}.{ext}"

    @staticmethod
    def clip_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}.{ext}"

    @staticmethod
    def last_frame_file_name(clip_index: int, ext: str) -> str:
        return f"clip{clip_index}-last-frame.{ext}"

    @staticmethod
    def join_name(end_clip_index: int) -> str:
        return f"join-{end_clip_index}"


class _StoredArtifact:
    def __init__(self, public_url: str = "") -> None:
        self._public_url = public_url

    def public_url(self) -> str:
        return self._public_url


def _artifact_public_url(artifact: Any, fallback: str = "") -> str:
    value = getattr(artifact, "public_url", "")
    if callable(value):
        return string_value(value())
    return string_value(value) or fallback
