"""Task artifact materialization, file inspection, and nested URL resolution."""

from __future__ import annotations

from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_support import _StoredArtifact, _TaskArtifactNaming
from backend.services.task_material_factory import TaskMaterialFactory
from backend.shared import string_value


class TaskArtifactStorage:
    def __init__(self, local_media_artifact_service: Any | None = None) -> None:
        self._local_media_artifact_service = local_media_artifact_service
        self._material_factory = TaskMaterialFactory(local_media_artifact_service)

    def normalize_optional(
        self, task: TaskRecord, source_url: str, target_file_name: str
    ) -> None:
        if not string_value(source_url) or not string_value(target_file_name):
            return
        if self._local_media_artifact_service:
            try:
                self._local_media_artifact_service.materialize_artifact(
                    source_url,
                    _TaskArtifactNaming.task_running_relative_dir(task),
                    target_file_name,
                )
            except Exception:  # noqa: S110 — best-effort materialization
                pass

    def normalize(
        self,
        task: TaskRecord,
        source_url: str,
        target_file_name: str,
        fallback_kind: str,
    ) -> Any:
        resolved = string_value(target_file_name)
        if not resolved:
            if fallback_kind == "storyboard":
                resolved = _TaskArtifactNaming.storyboard_file_name(task, "bin")
            elif fallback_kind == "keyframe":
                resolved = _TaskArtifactNaming.clip_frame_file_name(1, "first", "bin")
            else:
                resolved = _TaskArtifactNaming.clip_file_name(1, "bin")
        if self._local_media_artifact_service:
            return self._local_media_artifact_service.materialize_artifact(
                source_url,
                _TaskArtifactNaming.task_running_relative_dir(task),
                resolved,
            )
        return _StoredArtifact(public_url=source_url)

    def file_size(self, absolute_path: str) -> int:
        return self._material_factory.file_size(absolute_path)

    def resolve_absolute_path(self, file_url: str) -> str:
        return self._material_factory.resolve_absolute_path(file_url)

    def extract_last_frame_url(self, value: Any) -> str:
        direct = self._find_nested_string(value, "lastFrameUrl", "last_frame_url")
        return direct or self._find_nested_role_url(value, "last_frame")

    def _find_nested_string(self, value: Any, *keys: str) -> str:
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
                if isinstance(candidate, dict):
                    nested = self._find_nested_string(candidate, "url", "href", "uri")
                    if nested:
                        return nested
            for nested in value.values():
                resolved = self._find_nested_string(nested, *keys)
                if resolved:
                    return resolved
        elif isinstance(value, list):
            for item in value:
                resolved = self._find_nested_string(item, *keys)
                if resolved:
                    return resolved
        return ""

    def _find_nested_role_url(self, value: Any, role: str) -> str:
        if isinstance(value, dict):
            if string_value(value.get("role")).lower() == role:
                resolved = self._find_nested_string(
                    value.get("image_url") or value.get("imageUrl"), "url", "href", "uri"
                )
                if resolved:
                    return resolved
            for nested in value.values():
                resolved = self._find_nested_role_url(nested, role)
                if resolved:
                    return resolved
        elif isinstance(value, list):
            for item in value:
                resolved = self._find_nested_role_url(item, role)
                if resolved:
                    return resolved
        return ""
